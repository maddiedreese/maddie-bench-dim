"""Real DimOS modules: simulation execution and independent audit subscriber."""
import base64
import json
import os
import queue
import threading
import time
from pathlib import Path
from dimos.core.module import Module, ModuleConfig
from dimos.core.core import rpc
from dimos.core.stream import In, Out
from dimos.core.coordination.blueprints import autoconnect
from .config import ROOT
from .protocol import Batch
from .sim import PaintSim, MotionError, PreflightError

class PaintConfig(ModuleConfig):
    run_dir: str = str(ROOT/'runs/live')

class PaintModule(Module):
    config: PaintConfig
    telemetry: Out[dict]

    @rpc
    def start(self):
        super().start()
        self._queue=queue.Queue(maxsize=1)
        self._stop=threading.Event()
        self._ready=threading.Event()
        self._snapshot={'state':'starting'}
        self._lock=threading.Lock()
        self._thread=threading.Thread(target=self._worker,daemon=True)
        self._thread.start()
        if not self._ready.wait(45):raise RuntimeError('Simulation startup timed out')
        if self._snapshot['state']=='error':raise RuntimeError(self._snapshot['error'])

    def _publish(self,sim,state=None,error=None):
        folder=Path(self.config.run_dir);folder.mkdir(parents=True,exist_ok=True)
        if state is not None:self._state=state
        # Renderer stays on one thread throughout its lifetime.
        for name in ['overview','overhead']:
            tmp=folder/(name+'.tmp.jpg')
            sim.render(name,noise=name=='overhead').save(tmp,quality=90)
            tmp.replace(folder/(name+'.jpg'))
        sim.canvas.save(folder/'paper.tmp.png')
        (folder/'paper.tmp.png').replace(folder/'paper.png')
        snapshot={'state':self._state,'run_dir':str(folder),'provisional':True,'force_target_N':sim.force_target,'force_estimate_N':sim.force_control.filtered,**sim.stats()}
        if error:snapshot['error']=error
        with self._lock:self._snapshot=snapshot
        self.telemetry.publish(snapshot)
        (folder/'status.tmp.json').write_text(json.dumps(snapshot))
        (folder/'status.tmp.json').replace(folder/'status.json')

    def _worker(self):
        sim=None
        try:
            sim=PaintSim(render=True);self._sim=sim
            self._state='ready';self._publish(sim)
            self._ready.set()
            sim.on_tick=lambda:self._publish(sim)
            while not self._stop.is_set():
                try:job=self._queue.get(timeout=.1)
                except queue.Empty:continue
                kind,payload=job
                if kind=='begin':
                    sim.started=time.monotonic();self._publish(sim,'ready')
                elif kind=='draw':
                    batch,realtime=payload
                    self._publish(sim,'drawing')
                    try:
                        result=sim.execute(batch,realtime=realtime)
                        self._publish(sim,'ready')
                        with self._lock:self._snapshot['last_result']=result
                    except PreflightError as exc:
                        self._publish(sim,'rejected',str(exc))
                    except MotionError as exc:
                        sim.cancelled=True
                        self._publish(sim,'error',str(exc))
                    finally:sim.save(self.config.run_dir)
                elif kind=='observe':self._publish(sim)
                elif kind=='finish':
                    self._publish(sim,'finished');sim.save(self.config.run_dir)
        except Exception as exc:
            with self._lock:self._snapshot={'state':'error','error':f'{type(exc).__name__}: {exc}'}
            self._ready.set()
        finally:
            if sim is not None:
                sim.save(self.config.run_dir);sim.close()

    @rpc
    def begin_run(self) -> bool:
        self._queue.put_nowait(('begin',None));return True

    @rpc
    def submit(self,commands: str,realtime: bool=True) -> bool:
        batch=Batch.model_validate_json(commands)
        with self._lock:
            if self._snapshot['state'] not in ('ready','rejected'):raise RuntimeError('Simulation is not ready')
            self._snapshot['state']='queued'
        self._queue.put_nowait(('draw',(batch,realtime)))
        return True

    @rpc
    def status(self) -> dict:
        with self._lock:return dict(self._snapshot)

    @rpc
    def observation(self) -> str:
        return base64.b64encode((Path(self.config.run_dir)/'overhead.jpg').read_bytes()).decode()

    @rpc
    def finish(self) -> bool:
        self._queue.put_nowait(('finish',None));return True

    @rpc
    def cancel(self) -> bool:
        self._sim.cancelled=True;return True

    @rpc
    def stop(self):
        if hasattr(self,'_stop'):
            self._stop.set()
            if hasattr(self,'_sim'):self._sim.cancelled=True
            self._thread.join(timeout=10)
        super().stop()

class AuditModule(Module):
    config: PaintConfig
    telemetry: In[dict]

    @rpc
    def start(self):
        super().start()
        folder=Path(self.config.run_dir);folder.mkdir(parents=True,exist_ok=True)
        self._path=folder/'dimos-events.jsonl'
        self._count=0
        self._subscription=self.telemetry.subscribe(self._record)

    def _record(self,event):
        with self._path.open('a') as f:f.write(json.dumps(event)+'\n')
        self._count+=1

    @rpc
    def event_count(self) -> int:
        return self._count

    @rpc
    def stop(self):
        if hasattr(self,'_subscription'):self._subscription()
        super().stop()


def blueprint(run_dir):
    return autoconnect(PaintModule.blueprint(run_dir=str(run_dir)),AuditModule.blueprint(run_dir=str(run_dir))).global_config(simulation="mujoco",viewer='none',n_workers=2)

paint_blueprint=blueprint(os.environ.get('MADDIE_DIM_RUN_DIR',ROOT/'runs/live'))
