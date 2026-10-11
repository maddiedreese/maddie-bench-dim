import argparse
from .config import ROOT

def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    p=argparse.ArgumentParser(description='DimOS OpenYAM painting benchmark')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['demo','astra']:
        s=sub.add_parser(name);s.add_argument('--run-dir');s.add_argument('--realtime',action='store_true')
    s=sub.add_parser('serve');s.add_argument('--port',type=int,default=8765)
    sub.add_parser('doctor')
    args=p.parse_args()
    if args.command in ('demo','astra'):
        from .runner import run
        run(args.command,args.realtime,args.run_dir)
    elif args.command=='serve':
        from .dashboard import serve
        serve(args.port)
    else:
        import importlib.metadata as im
        import json,platform
        print(json.dumps({'platform':platform.platform(),'architecture':platform.machine(),'root':str(ROOT),'dimos':im.version('dimos'),'mujoco':im.version('mujoco'),'hardware_validated':False},indent=2))

if __name__=='__main__':main()
