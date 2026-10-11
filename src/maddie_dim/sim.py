"""Rigid-body dynamics, bounded trajectories and contact-driven marks."""
import json
import math
import time
from pathlib import Path
import numpy as np
import mujoco
from PIL import Image, ImageDraw
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from .scene import build_scene
from .config import config
from .protocol import Batch
from .frame import RIGHT, DOWN, NORMAL
from .control import NormalForceControl, estimate_normal_force

class MotionError(RuntimeError):
    pass

class PreflightError(MotionError):
    pass

class DeadlineReached(MotionError):
    pass

class PaintSim:
    def __init__(self, c=None, render=False):
        self.c = c or config()
        self.model = mujoco.MjModel.from_xml_path(str(build_scene(self.c)))
        self.data = mujoco.MjData(self.model)
        self.ik_data = mujoco.MjData(self.model)
        self.tip_id = self.model.site('tip').id
        self.nib_id = self.model.geom('nib_contact').id
        self.paper_id = self.model.geom('paper').id
        self.center = np.array(self.c['paper_center_m'])
        self.canvas = Image.new('RGB', (840,1188), 'white')
        self.draw = ImageDraw.Draw(self.canvas)
        self.last_contact = None
        self.last_point = None
        self.contact_steps = 0
        self.distance_mm = 0.
        self.peak_force = 0.
        self.max_tracking_error_mm = 0.
        self.max_planar_error_mm = 0.
        self.force = 0.
        self.force_control=NormalForceControl()
        self.force_target=None
        self.estimated_force=0.
        self.force_offset_q=np.zeros(6)
        self._next_control=0.
        self._previous_velocity=np.zeros(6)
        self.contact_lost_steps = 0
        self.renderer = None
        self.render_enabled = render
        self.qtarget = np.array([0.,1.8,1.5,-1.,0.,0.])
        self.qtarget = self.ik(self.world([105,148.5],.025), self.qtarget)
        self.dqtarget = np.zeros(6)
        self.ddqtarget = np.zeros(6)
        self.data.qpos[:6] = self.qtarget
        mujoco.mj_forward(self.model,self.data)
        self.started = None
        self.deadline = self.c['deadline_seconds']
        self.on_tick = None
        self.cancelled = False
        self.trace = []
        self._next_log=0.
        self._next_frame=0.
        self.motor_rng=np.random.default_rng(self.c['seed'])
        self.camera_rng=np.random.default_rng(self.c['seed']+1)

    def world(self, point, height=0.):
        x,y=point
        return self.center + RIGHT*(x-105)/1000 + DOWN*(y-148.5)/1000 + NORMAL*height

    def paper_xy(self, position):
        delta=position-self.center
        return np.array([np.dot(delta,RIGHT)*1000+105,np.dot(delta,DOWN)*1000+148.5])

    def tip(self):
        return self.data.site_xpos[self.tip_id].copy()

    def ik(self, target, seed):
        def error(q):
            self.ik_data.qpos[:6]=q
            self.ik_data.qpos[6]=0
            mujoco.mj_forward(self.model,self.ik_data)
            r=self.ik_data.site_xmat[self.tip_id].reshape(3,3)
            desired=Rotation.from_euler('xyz',[np.pi,0,np.pi/2]).as_matrix()
            return np.r_[self.ik_data.site_xpos[self.tip_id]-target, .10*Rotation.from_matrix(desired@r.T).as_rotvec()]
        bounds=(self.model.jnt_range[:6,0]+.002,self.model.jnt_range[:6,1]-.002)
        fit=least_squares(error,np.clip(seed,*bounds),bounds=bounds,max_nfev=100,ftol=1e-8,xtol=1e-8,gtol=1e-9)
        err=error(fit.x)
        if np.linalg.norm(err[:3]) > .00015 or np.linalg.norm(err[3:])>.001:
            raise PreflightError(f'Unreachable pen pose {target.tolist()}; residual {np.linalg.norm(err[:3])*1000:.3f} mm')
        return fit.x

    def plan(self, batch: Batch):
        """Preflight every segment before executing any of the batch."""
        q=self.qtarget.copy()
        self.ik_data.qpos[:6]=q;self.ik_data.qpos[6]=0
        mujoco.mj_forward(self.model,self.ik_data)
        pos=self.ik_data.site_xpos[self.tip_id].copy()
        trajectory=[]
        def line(target,speed,ink,force=None):
            nonlocal q,pos
            start=pos.copy()
            n=max(1,math.ceil(np.linalg.norm(target-start)/.003))
            for k in range(1,n+1):
                p=start+(target-start)*k/n
                qnext=self.ik(p,q)
                for ct in self.ik_data.contact:
                    if ct.dist < -.0005 and {int(ct.geom1),int(ct.geom2)} != {self.nib_id,self.paper_id}:
                        raise PreflightError(f'Planned collision: {self.model.geom(ct.geom1).name} / {self.model.geom(ct.geom2).name}')
                dq=np.max(np.abs(qnext-q))
                # Quintic smoothstep: maximum first derivative 1.875,
                # maximum second derivative 5.774. Stop at sample knots.
                duration=max(1.875*np.linalg.norm(p-pos)/(speed/1000),1.875*dq/self.c['joint_velocity_max_rad_s'],math.sqrt(5.774*dq/self.c['joint_acceleration_max_rad_s2']),.04)
                trajectory.append((q.copy(),qnext.copy(),duration,ink,p.copy(),force))
                q=qnext;pos=p
        for stroke in batch.strokes:
            clearance=max(.012,pos[2]-self.center[2])
            line(np.array([pos[0],pos[1],self.center[2]+clearance]),20,False)
            line(self.world(stroke.points[0],clearance),30,False)
            line(self.world(stroke.points[0],-self.c['contact_indentation_mm']/1000),5,False)
            for point in stroke.points[1:]:
                line(self.world(point,-self.c['contact_indentation_mm']/1000),stroke.speed_mm_s,True,stroke.force_N)
            line(self.world(stroke.points[-1],.012),8,False)
        if batch.strokes:
            line(np.array([pos[0],pos[1],self.center[2]+.065]),20,False)
            line(np.array([.16,.23,.13]),30,False)
        return trajectory

    def elapsed(self):
        return 0. if self.started is None else time.monotonic()-self.started

    def execute(self, batch, realtime=False):
        trajectory=self.plan(batch)
        estimate=sum(t[2] for t in trajectory)
        if self.started is not None and self.elapsed()+estimate>self.deadline:
            raise DeadlineReached('Batch exceeds the remaining 30-minute wall-clock budget; send fewer strokes')
        for q0,q1,duration,ink,target,force in trajectory:
            steps=math.ceil(duration/self.model.opt.timestep)
            begin=time.monotonic()
            for i in range(1,steps+1):
                if self.cancelled:
                    raise MotionError('Run stopped')
                if self.started is not None and self.elapsed()>=self.deadline:
                    raise DeadlineReached('30-minute wall-clock limit reached')
                u=i/steps;s=10*u**3-15*u**4+6*u**5
                self.qtarget=q0+(q1-q0)*s
                actual_duration=steps*self.model.opt.timestep
                self.dqtarget=(q1-q0)*(30*u**2-60*u**3+30*u**4)/actual_duration
                self.ddqtarget=(q1-q0)*(60*u-180*u**2+120*u**3)/actual_duration**2
                self.force_target=force
                self.step(ink)
                if realtime:
                    wait=begin+i*self.model.opt.timestep-time.monotonic()
                    if wait>0: time.sleep(wait)
            self.max_tracking_error_mm=max(self.max_tracking_error_mm,float(np.linalg.norm(self.tip()-target)*1000))
            self.max_planar_error_mm=max(self.max_planar_error_mm,float(np.linalg.norm(self.paper_xy(self.tip())-self.paper_xy(target))))
        return {'planned_motion_seconds':estimate,**self.stats()}

    def step(self, expected_ink=False):
        kp=np.array([80,80,80,10,10,10])
        kd=np.array([5,5,5,1.5,1.5,1.5])
        mass=np.zeros((self.model.nv,self.model.nv))
        mujoco.mj_fullM(self.model,self.data,mass)
        if self.data.time>=self._next_control:
            jp=np.zeros((3,self.model.nv));jr=np.zeros_like(jp)
            mujoco.mj_jacSite(self.model,self.data,jp,jr,self.tip_id)
            jac=np.vstack((jp[:,:6],jr[:,:6]))
            motor=self.data.qfrc_actuator[:6]+self.motor_rng.normal(0,.003,6)
            acceleration=(self.data.qvel[:6]-self._previous_velocity)/self.c['control_dt_s']
            self._previous_velocity=self.data.qvel[:6].copy()
            self.estimated_force=estimate_normal_force(mass[:6,:6],acceleration,self.data.qfrc_bias[:6],self.data.qfrc_passive[:6],motor,jac,NORMAL)
            offset=self.force_control.update(self.estimated_force,self.force_target,self.c['control_dt_s'])
            self.force_offset_q=np.linalg.lstsq(jac,np.r_[NORMAL*offset,[0,0,0]],rcond=1e-4)[0]
            qcmd=self.qtarget+self.force_offset_q
            if np.any(qcmd<self.model.jnt_range[:6,0]) or np.any(qcmd>self.model.jnt_range[:6,1]):
                raise MotionError('Force correction would exceed joint limits')
            self.data.ctrl[:]=np.clip(kp*(qcmd-self.data.qpos[:6])+kd*(self.dqtarget-self.data.qvel[:6])+self.data.qfrc_bias[:6]+mass[:6,:6]@self.ddqtarget,-10,10)
            self._next_control=self.data.time+self.c['control_dt_s']-1e-9
        mujoco.mj_step(self.model,self.data)
        if not np.all(np.isfinite(self.data.qpos)):
            raise MotionError('Nonfinite physics state')
        self.force=0.
        unexpected=[]
        for idx in range(self.data.ncon):
            ct=self.data.contact[idx]
            pair={int(ct.geom1),int(ct.geom2)}
            f=np.zeros(6);mujoco.mj_contactForce(self.model,self.data,idx,f)
            if pair=={self.nib_id,self.paper_id}:
                self.force+=max(0.,float(f[0]))
            elif abs(f[0])>.1:
                unexpected.append((self.model.geom(ct.geom1).name,self.model.geom(ct.geom2).name,float(f[0])))
        self.peak_force=max(self.peak_force,self.force)
        if unexpected:
            raise MotionError(f'Unexpected collision: {unexpected[0]}')
        if self.force>self.c['force_abort_N']:
            raise MotionError(f'Contact force {self.force:.2f} N exceeds simulation abort threshold')
        xy=self.paper_xy(self.tip())
        # Deposition uses actual measured contact regardless of commanded pen state.
        if self.force>.015 and 0<=xy[0]<=210 and 0<=xy[1]<=297:
            pt=tuple(xy*4)
            # Provisional, bounded force-response law, NOT measured POSCA data.
            width=max(1,round(np.clip(.7*(max(self.force,.01)/.25)**.12,.5,.85)*4))
            tone=int(np.clip(100-85*(1-np.exp(-self.force/.12)),15,100))
            color=(tone,tone,tone)
            previous=self.last_contact if self.last_contact is not None else pt
            if self.last_contact is not None:
                self.distance_mm+=float(np.linalg.norm(xy-self.last_point))
            radius=width/2
            left=max(0,math.floor(min(previous[0],pt[0])-radius-1))
            top=max(0,math.floor(min(previous[1],pt[1])-radius-1))
            right=min(self.canvas.width,math.ceil(max(previous[0],pt[0])+radius+2))
            bottom=min(self.canvas.height,math.ceil(max(previous[1],pt[1])+radius+2))
            patch=Image.new('RGB',(right-left,bottom-top),'white')
            pd=ImageDraw.Draw(patch)
            pp=(previous[0]-left,previous[1]-top);ep=(pt[0]-left,pt[1]-top)
            pd.line([pp,ep],fill=color,width=width)
            pd.ellipse([ep[0]-radius,ep[1]-radius,ep[0]+radius,ep[1]+radius],fill=color)
            old=np.asarray(self.canvas.crop((left,top,right,bottom)))
            self.canvas.paste(Image.fromarray(np.minimum(old,np.asarray(patch))),(left,top))
            self.last_contact=pt;self.last_point=xy.copy();self.contact_steps+=1
        else:
            self.last_contact=None;self.last_point=None
            if expected_ink: self.contact_lost_steps+=1
        if self.data.time>=self._next_log:
            self.trace.append({'t':round(self.data.time,4),'wall_s':round(self.elapsed(),4),'q':self.data.qpos[:6].tolist(),'q_command':self.qtarget.tolist(),'tip_m':self.tip().tolist(),'force_N':self.force,'force_estimate_N':self.estimated_force,'force_target_N':self.force_target,'force_offset_m':self.force_control.offset,'expected_ink':expected_ink})
            self._next_log=self.data.time+.02
        if self.on_tick and self.data.time>=self._next_frame:
            self.on_tick();self._next_frame=self.data.time+.5

    def stats(self):
        return {'sim_seconds':round(self.data.time,3),'wall_seconds':round(self.elapsed(),3),'contact_seconds':round(self.contact_steps*self.model.opt.timestep,3),'drawn_distance_mm':round(self.distance_mm,2),'peak_force_N':round(self.peak_force,3),'max_tracking_error_mm':round(self.max_tracking_error_mm,3),'max_planar_error_mm':round(self.max_planar_error_mm,3),'contact_lost_seconds':round(self.contact_lost_steps*self.model.opt.timestep,3)}

    def render(self,camera='overhead',noise=True):
        if self.renderer is None:
            self.renderer=mujoco.Renderer(self.model,height=self.c['camera_height'],width=self.c['camera_width'])
        tid=self.model.texture('paint').id
        addr=self.model.tex_adr[tid]
        # MuJoCo box top-face UVs map raw image rows to paper +Y (top).
        pixels=np.asarray(self.canvas).copy().reshape(-1)
        self.model.tex_data[addr:addr+pixels.size]=pixels
        mujoco.mjr_uploadTexture(self.model,self.renderer._mjr_context,tid)
        self.renderer.update_scene(self.data,camera=camera)
        im=self.renderer.render().copy()
        if noise:
            im=np.clip(im.astype(float)+self.camera_rng.normal(0,self.c['camera_noise_sigma'],im.shape),0,255).astype(np.uint8)
        return Image.fromarray(im)

    def save(self,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        self.canvas.save(folder/'paper.png')
        (folder/'physics.json').write_text(json.dumps(self.stats(),indent=2))
        with (folder/'trajectory.jsonl').open('w') as f:
            for row in self.trace:f.write(json.dumps(row)+'\n')

    def close(self):
        if self.renderer is not None:
            self.renderer.close();self.renderer=None
