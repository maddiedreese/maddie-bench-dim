"""Local read-only review UI for recorded and live benchmark runs."""

import json
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from .config import ROOT

app = FastAPI()


def run_path(run_id):
    p = (ROOT / "runs" / run_id).resolve()
    if p.parent != (ROOT / "runs").resolve() or not p.is_dir():
        raise HTTPException(404)
    return p


@app.get("/api/runs")
def runs():
    result = []
    for p in sorted((ROOT / "runs").glob("*/manifest.json"), reverse=True):
        try:
            m = json.loads(p.read_text())
            m["id"] = p.parent.name
            status = p.parent / "status.json"
            if status.exists():
                m["live"] = json.loads(status.read_text())
                m["live"]["elapsed_now_seconds"] = m["live"].get("wall_seconds", 0)
                if m["status"] not in ("completed", "failed", "time_limit"):
                    m["live"]["elapsed_now_seconds"] += max(
                        0, time.time() - status.stat().st_mtime
                    )
            turns = sorted(p.parent.glob("turn-*"))
            if turns:
                latest = turns[-1]
                commands = latest / "commands.json"
                if commands.exists():
                    m["intent"] = json.loads(commands.read_text()).get("note", "")
                elif (latest / "request.json").exists():
                    m["intent"] = (
                        "Astra is inspecting the camera and planning its next strokes."
                    )
            m["artifacts"] = [
                name
                for name in [
                    "manifest.json",
                    "trajectory.jsonl",
                    "physics.json",
                    "dimos-events.jsonl",
                    "analysis.json",
                    "review-timelapse.mp4",
                ]
                if (p.parent / name).is_file()
                and (
                    name != "review-timelapse.mp4"
                    or m["status"] in ("completed", "failed", "time_limit")
                )
            ]
            result.append(m)
        except (ValueError, OSError):
            continue
    return result


@app.get("/artifact/{run_id}/{filename}")
def artifact(run_id: str, filename: str):
    if filename not in {
        "overview.jpg",
        "overhead.jpg",
        "paper.png",
        "manifest.json",
        "trajectory.jsonl",
        "physics.json",
        "dimos-events.jsonl",
        "analysis.json",
        "review-timelapse.mp4",
        "recording.json",
    }:
        raise HTTPException(404)
    p = run_path(run_id) / filename
    if not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, headers={"Cache-Control": "no-store"})


@app.get("/reference.jpg")
def reference():
    return FileResponse(ROOT / "assets/reference.jpg")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Maddie Bench · DimOS</title><style>
:root{font-family:ui-sans-serif,system-ui,sans-serif;color:#e8e7e2;background:#141717}*{box-sizing:border-box}body{margin:0}header{display:flex;justify-content:space-between;align-items:center;padding:24px 32px;border-bottom:1px solid #363b38}h1{font-size:23px;margin:0;font-weight:550;letter-spacing:-.7px}header small{font-size:12px;color:#9da69f}select{max-width:310px;background:#242b27;color:#eee;border:1px solid #455147;padding:9px;border-radius:8px}main{max-width:1500px;margin:auto;padding:24px 32px}.tag{color:#c1de99;font-size:12px;letter-spacing:1.2px;text-transform:uppercase}.intro{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:20px}h2{font-size:30px;font-weight:500;letter-spacing:-1px;margin:8px 0}.muted{color:#9da69f;font-size:13px;line-height:1.6}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.stat{padding:16px 18px;background:#202622;border:1px solid #343d34;border-radius:10px}.stat b{display:block;font-size:23px;margin-top:5px;font-weight:500}.grid{display:grid;grid-template-columns:1.6fr 1fr;gap:18px}.panel{border:1px solid #343d34;border-radius:12px;overflow:hidden;background:#1b201d}.label{padding:14px 18px;font-size:13px;display:flex;justify-content:space-between}.mainimg{width:100%;height:530px;object-fit:contain;background:#101210}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1px}.pair img{width:100%;height:270px;object-fit:contain;background:#efede6}.camera{width:100%;height:220px;object-fit:contain;background:#101210}.note{margin:20px 0;padding:16px 18px;border-left:3px solid #d3ac72;background:#24231e;color:#d0c7b7;font-size:13px;line-height:1.65}.links{display:flex;gap:22px;flex-wrap:wrap}a{color:#c1de99;font-size:13px}footer{margin-top:24px;color:#869087;font-size:12px}#error{color:#edbda3}.badge{font-size:11px;border:1px solid #6b775e;padding:3px 7px;border-radius:5px}@media(max-width:800px){header,main{padding:18px}.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}.mainimg{height:400px}.intro{display:block}select{max-width:190px}}
</style></head><body><header><div><h1>maddie-bench <span style="color:#a4c587">/ dim</span></h1><small>Dimensional OS × Anvil OpenYAM</small></div><select id="runs" aria-label="Select run"></select></header><main><div class="intro"><div><div class="tag">Physical drawing benchmark</div><h2 id="title">A portrait, one physical stroke at a time.</h2><div class="muted">Black POSCA PC-1MR · A4 portrait · camera feedback · 30-minute wall clock</div></div><span class="badge" id="state">Waiting for a run</span></div><div class="stats"><div class="stat"><span class="muted">Wall time / 30 min</span><b id="clock">—</b></div><div class="stat"><span class="muted">Force target</span><b id="force">—</b></div><div class="stat"><span class="muted">Peak actual force</span><b id="peak">—</b></div><div class="stat"><span class="muted">Actual ink path</span><b id="distance">—</b></div></div><div class="grid"><section class="panel"><div class="label">MuJoCo scene <span class="muted">Actual articulated dynamics</span></div><img class="mainimg" id="overview" alt="Simulated OpenYAM drawing on portrait paper"></section><section class="panel"><div class="label">Reference / deposited marks</div><div class="pair"><img src="/reference.jpg" alt="Original maddie-bench reference"><img id="paper" alt="Actual contact-driven marks"></div><div class="label">Model’s overhead camera <span class="muted">Includes occlusion</span></div><img class="camera" id="overhead" alt="Camera observation provided to Astra"></section></div><div class="note"><strong>Simulation evidence, pending physical calibration.</strong> Robot model provenance contains an unresolved DimOS planning/gravity-model mismatch. Pen pressure response, grip placement and camera optics are provisional. The force controller uses a motor-torque estimate; actual simulated force is shown for evaluation. A calibration demo is not an Astra result.</div><p class="muted" id="intent"></p><p id="error"></p><div class="links" id="links"></div><footer>Every attempt retains its commands, camera observations, physics trace, DimOS events, model response and configuration hashes. No API key is exposed by this viewer.</footer></main><script>
let selected='',runList=[];const el=id=>document.getElementById(id);el('runs').onchange=()=>{selected=el('runs').value;update()};
async function update(){try{runList=await(await fetch('/api/runs')).json();const list=runList.map(r=>r.id);if(!selected&&list.length)selected=list[0];const select=el('runs');if(JSON.stringify([...select.options].map(o=>o.value))!==JSON.stringify(list)){select.replaceChildren(...runList.map(r=>{let o=document.createElement('option');o.value=r.id;o.textContent=r.mode+' · '+r.id;return o}));}select.value=selected;let r=runList.find(x=>x.id===selected);if(!r)return;let s=r.live||{};el('title').textContent=r.mode==='demo'?'Pressure and motion calibration.':'Astra paints Maddie.';el('state').textContent=(['failed','time_limit'].includes(r.status)?r.status:s.state||r.status)+(r.mode==='demo'?' · no model call':'');el('clock').textContent=(s.elapsed_now_seconds||s.wall_seconds||0).toFixed(1)+' s';el('force').textContent=s.force_target_N==null?'Pen lifted':s.force_target_N.toFixed(2)+' N';el('peak').textContent=(s.peak_force_N||0).toFixed(2)+' N';el('distance').textContent=(s.drawn_distance_mm||0).toFixed(0)+' mm';el('error').textContent=r.error||s.error||'';el('intent').textContent=r.intent||'';for(let [id,file] of [['overview','overview.jpg'],['overhead','overhead.jpg'],['paper','paper.png']])el(id).src='/artifact/'+selected+'/'+file+'?t='+Date.now();el('links').replaceChildren(...(r.artifacts||[]).map(name=>{let a=document.createElement('a');a.href='/artifact/'+selected+'/'+name;a.textContent=name;return a}));}catch(e){el('error').textContent='Waiting for local run data'}}update();setInterval(update,1500);
</script></body></html>"""


def serve(port=8765):
    uvicorn.run(app, host="127.0.0.1", port=port)
