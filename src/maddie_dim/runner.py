import base64
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from dimos.core.coordination.module_coordinator import ModuleCoordinator
from .config import ROOT, config
from .modules import PaintModule, AuditModule, blueprint
from .protocol import Batch
from .policy import Astra


def demo_batch():
    # A calibration coupon, deliberately not a fabricated Astra portrait.
    return Batch.model_validate({'strokes':[
        {'points':[[65,110],[145,110]],'force_N':.08},
        {'points':[[65,135],[145,135]],'force_N':.25},
        {'points':[[65,160],[145,160]],'force_N':.6},
        {'points':[[85,190],[105,175],[125,190],[105,205],[85,190]],'force_N':.25}
    ],'done':True,'note':'Controller calibration: three force levels and a closed contour. No model call.'})


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wait_motion(module,deadline=None):
    while True:
        state=module.status()
        if state['state'] not in ('queued','drawing'):return state
        if deadline is not None and time.monotonic()>=deadline:
            module.cancel();raise TimeoutError('30-minute wall-clock deadline')
        time.sleep(.2)


def run(mode='demo',realtime=False,run_dir=None):
    folder=Path(run_dir) if run_dir else ROOT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True,exist_ok=False)
    c=config()
    if mode=='astra':realtime=True
    manifest={'mode':mode,'protocol':c['protocol'],'config':c,'reference_sha256':sha(ROOT/'assets/reference.jpg'),'config_sha256':sha(ROOT/'configs/benchmark.json'),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/maddie_dim').glob('*.py'))},'dimos_commit':'1e7b4918bc626de4fa6592fb023d4b3aee932754','started_utc':datetime.now(timezone.utc).isoformat(),'physical_transfer':'UNVERIFIED','pen_response':'UNCALIBRATED','status':'starting','realtime':realtime}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
    coordinator=None
    try:
        policy=Astra(ROOT,folder) if mode=='astra' else None
        coordinator=ModuleCoordinator.build(blueprint(folder))
        module=coordinator.get_instance(PaintModule)
        audit=coordinator.get_instance(AuditModule)
        start=time.monotonic();deadline=start+c['deadline_seconds']
        module.begin_run();time.sleep(.15)
        if mode=='demo':
            batch=demo_batch();(folder/'commands.json').write_text(batch.model_dump_json(indent=2))
            module.submit(batch.model_dump_json(),realtime)
            final=wait_motion(module)
            if final['state'] in ('error','rejected'):raise RuntimeError(final.get('error'))
        else:
            feedback={}
            for turn in range(100):
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('30-minute wall-clock deadline')
                camera=Image.open(io.BytesIO(base64.b64decode(module.observation())))
                batch=policy.next(camera,remaining,feedback)
                if time.monotonic()>=deadline:raise TimeoutError('Astra returned after deadline; no motion executed')
                if batch.strokes:
                    module.submit(batch.model_dump_json(),True)
                    state=wait_motion(module,deadline)
                    # Only measured/estimated observations are exposed to model.
                    feedback={k:state[k] for k in ('state','error','wall_seconds','force_estimate_N') if k in state}
                    if state['state']=='error':raise RuntimeError(state.get('error'))
                if batch.done and (not batch.strokes or state['state']=='ready'):break
            else:raise RuntimeError('Turn limit reached')
        module.finish();time.sleep(.5)
        manifest['status']='completed'
        manifest['dimos_audit_events']=audit.event_count()
        if manifest['dimos_audit_events']<1:raise RuntimeError('DimOS audit stream delivered no events')
    except Exception as exc:
        manifest['status']='failed';manifest['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        if coordinator is not None:coordinator.stop()
        manifest['finished_utc']=datetime.now(timezone.utc).isoformat()
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
        print(f'Run artifacts: {folder}',flush=True)
    return folder
