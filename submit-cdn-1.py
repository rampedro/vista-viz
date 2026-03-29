
from flask import Flask, render_template_string, jsonify, request
import os, re, subprocess, time

app = Flask(__name__)

# --- THE UI (Auto-Deconstruct Dashboard) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vista // NLP Code Deconstructor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
        textarea { background: #0f172a !important; color: #38bdf8 !important; font-family: 'Fira Code', monospace; border: 1px solid #1e293b; }
        .console { background: #000; height: 250px; overflow-y: auto; font-family: monospace; font-size: 11px; border: 1px solid #334155; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <header class="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
            <div>
                <h1 class="text-2xl font-black italic text-sky-400 tracking-tighter uppercase">Vista Engine v2.0</h1>
                <p class="text-[10px] text-slate-500 font-mono uppercase tracking-[0.2em]">NLP-Driven CDN Automator</p>
            </div>
            <div id="status" class="text-[10px] font-bold px-3 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">STANDBY</div>
        </header>

        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-8">
                <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Paste Full HTML/JS Bundle</label>
                <textarea id="code-input" class="w-full h-[500px] p-6 rounded-2xl mt-2 outline-none focus:border-sky-500 transition-all shadow-2xl" 
                    placeholder="Paste your entire Leaflet/GeoJSON HTML here..."></textarea>
            </div>

            <div class="col-span-4 space-y-6">
                <div class="glass p-5 rounded-2xl shadow-xl">
                    <h3 class="text-[11px] font-black text-slate-400 uppercase mb-4 tracking-widest">Deployment Settings</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="text-[9px] text-slate-500 uppercase">Target Repo</label>
                            <input id="repo-url" type="text" value="git@github.com:rampedro/vista-viz.git" class="w-full bg-slate-900/50 p-2 rounded border border-slate-700 text-xs mt-1 text-sky-300">
                        </div>
                        <div>
                            <label class="text-[9px] text-slate-500 uppercase">Version Tag</label>
                            <input id="version" type="text" value="v1.0.0" class="w-full bg-slate-900/50 p-2 rounded border border-slate-700 text-xs mt-1">
                        </div>
                        <button onclick="runPipeline()" class="w-full bg-sky-600 hover:bg-sky-500 py-4 rounded-xl font-black tracking-widest transition transform active:scale-95 shadow-lg shadow-sky-500/20">
                            DECONSTRUCT & PUSH
                        </button>
                    </div>
                </div>

                <div class="glass p-5 rounded-2xl shadow-xl">
                    <h3 class="text-[11px] font-black text-slate-400 uppercase mb-2 tracking-widest">Live Output</h3>
                    <div id="console" class="console p-3 rounded-lg border border-slate-800">
                        <div class="text-slate-600">// Ready for input...</div>
                    </div>
                </div>

                <div id="success-link" class="hidden p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                    <p class="text-[10px] text-emerald-400 font-bold uppercase mb-1">CDN Link Active:</p>
                    <code id="cdn-display" class="block text-[10px] bg-black/50 p-2 rounded text-emerald-200 break-all cursor-pointer"></code>
                </div>
            </div>
        </div>
    </div>

    <script>
        function log(m, type='info') {
            const colors = { info: 'text-slate-400', error: 'text-red-400', success: 'text-emerald-400' };
            const c = document.getElementById('console');
            c.innerHTML += `<div class="${colors[type]} mb-1">> ${m}</div>`;
            c.scrollTop = c.scrollHeight;
        }

        async function runPipeline() {
            const btn = document.querySelector('button');
            const code = document.getElementById('code-input').value;
            const repo = document.getElementById('repo-url').value;
            const version = document.getElementById('version').value;

            if(!code) return log("Input empty", 'error');
            
            btn.disabled = true;
            document.getElementById('status').innerText = "PROCESSING";
            log("Starting NLP Deconstruction...");

            const res = await fetch('/automate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code, repo, version})
            });
            
            const data = await res.json();
            btn.disabled = false;

            if(data.status === 'ok') {
                log("Files organized and pushed!", 'success');
                document.getElementById('status').innerText = "ONLINE";
                document.getElementById('success-link').classList.remove('hidden');
                document.getElementById('cdn-display').innerText = data.cdn_url;
            } else {
                log(data.message, 'error');
                document.getElementById('status').innerText = "FAILED";
            }
        }
    </script>
</body>
</html>
"""

# --- BACKEND AUTOMATION ---

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/automate', methods=['POST'])
def automate_pipeline():
    data = request.json
    raw_input = data['code']
    repo_url = data['repo']
    version = data['version']

    try:
        # 1. REGEX ENGINE: Deconstruct the code
        # Extract CSS
        css_match = re.search(r'<style>(.*?)</style>', raw_input, re.DOTALL)
        css = css_match.group(1).strip() if css_match else ""

        # Extract JS (Only scripts without 'src' attributes)
        js_blocks = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', raw_input, re.DOTALL)
        js = "\n\n".join(js_blocks).strip()

        # Extract HTML Fragment
        body_match = re.search(r'<body>(.*?)</body>', raw_input, re.DOTALL)
        html = body_match.group(1).strip() if body_match else ""

        # 2. FILE SYSTEM: Organize into /dist
        if not os.path.exists("dist"): os.makedirs("dist")
        
        # We always save a fresh index.js
        with open("dist/index.js", "w") as f:
            f.write(f"/* VISTA-AUTO: {version} */\n{js}")
        
        if css:
            with open("dist/style.css", "w") as f: f.write(css)
        if html:
            with open("dist/fragment.html", "w") as f: f.write(html)

        # 3. GIT AUTOMATION
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"])
            subprocess.run(["git", "checkout", "-b", "main"])

        # Configure temporary user for the push
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "Vista Robot"
        env["GIT_AUTHOR_EMAIL"] = "bot@vista.io"
        env["GIT_COMMITTER_NAME"] = "Vista Robot"
        env["GIT_COMMITTER_EMAIL"] = "bot@vista.io"

        # Force commit even if logic is same (Cache-Busting)
        with open("dist/.build_id", "w") as f: f.write(str(time.time()))

        subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "remote", "add", "origin", repo_url])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"Vista Auto-Build {version}"], env=env)
        
        # Tag Management
        subprocess.run(["git", "tag", "-d", version], stderr=subprocess.DEVNULL)
        subprocess.run(["git", "tag", "-a", version, "-m", "Release"], env=env)

        # 4. THE PUSH
        push = subprocess.run(["git", "push", "origin", "HEAD:main", "--tags", "--force"], 
                              capture_output=True, text=True, env=env)

        if push.returncode != 0:
            return jsonify({"status": "error", "message": f"Git Failure: {push.stderr}"})

        # 5. CDN URL GENERATOR
        repo_path = re.search(r"github\.com[:/](.+?/.+?)(?:\.git|$)", repo_url).group(1)
        cdn_url = f"https://cdn.jsdelivr.net/gh/{repo_path}@{version}/dist/index.js"

        return jsonify({"status": "ok", "cdn_url": cdn_url})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
