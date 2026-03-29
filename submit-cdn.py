from flask import Flask, render_template_string, jsonify, request, send_file
import os, re, subprocess

app = Flask(__name__)

# --- THE UI (Updated with URL Display) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vista Autonomous Pipeline</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
        textarea { background: #0f172a !important; color: #10b981 !important; font-family: 'Fira Code', monospace; border: 1px solid #1e293b; }
        .status-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
        .console { background: #000; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
            <h1 class="text-2xl font-black italic text-blue-500 tracking-tighter">VISTA // AUTO-DEPLOY</h1>
            <div id="pipeline-status" class="text-xs font-mono px-3 py-1 rounded bg-slate-800 text-slate-400">IDLE</div>
        </div>

        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-8">
                <div class="mb-4">
                    <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Library Source (JS)</label>
                    <textarea id="code-input" class="w-full h-80 p-4 rounded-xl mt-2 outline-none focus:border-blue-500" placeholder="function hello() { console.log('hi'); }"></textarea>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-[10px] font-bold text-slate-500 uppercase">GitHub Repo (SSH or HTTPS)</label>
                        <input id="repo-url" type="text" placeholder="github.com/username/repo" class="w-full bg-slate-900 p-2 rounded border border-slate-800 text-sm mt-1">
                    </div>
                    <div>
                        <label class="text-[10px] font-bold text-slate-500 uppercase">Version/Tag</label>
                        <input id="version" type="text" placeholder="v1.0.1" class="w-full bg-slate-900 p-2 rounded border border-slate-800 text-sm mt-1">
                    </div>
                </div>

                <div id="success-card" class="hidden mt-6 p-4 bg-blue-900/20 border border-blue-500/50 rounded-xl">
                    <h3 class="text-blue-400 font-bold text-sm mb-2">🚀 DEPLOYMENT COMPLETE</h3>
                    <div class="text-xs space-y-2">
                        <p class="text-slate-400">CDN URL:</p>
                        <code id="cdn-url" class="block bg-black p-2 rounded text-blue-300 break-all select-all"></code>
                        <a id="download-link" href="/download" class="inline-block mt-2 text-blue-400 underline font-bold">Download index.js</a>
                    </div>
                </div>
            </div>

            <div class="col-span-4 flex flex-col">
                <div class="mb-4">
                    <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Automation Logs</label>
                    <div id="console" class="console p-4 mt-2 rounded-xl border border-slate-800">
                        <div class="text-slate-600">// Pipeline Ready</div>
                    </div>
                </div>
                
                <button id="deploy-btn" onclick="triggerAutomation()" class="w-full bg-blue-600 hover:bg-blue-500 py-4 rounded-xl font-black tracking-widest transition active:scale-95 shadow-lg shadow-blue-500/20">
                    START AUTO-PIPELINE
                </button>
            </div>
        </div>
    </div>

    <script>
        function log(msg, color='text-slate-400') {
            const c = document.getElementById('console');
            const d = document.createElement('div');
            d.className = `mb-1 ${color}`;
            d.innerHTML = `> ${msg}`;
            c.appendChild(d);
            c.scrollTop = c.scrollHeight;
        }

        async function triggerAutomation() {
            const status = document.getElementById('pipeline-status');
            const code = document.getElementById('code-input').value;
            const repo = document.getElementById('repo-url').value;
            const version = document.getElementById('version').value;
            const successCard = document.getElementById('success-card');

            if(!code || !repo || !version) { log("Error: Missing Data", "text-red-500"); return; }
            successCard.classList.add('hidden');

            status.innerText = "PACKAGING...";
            status.className = "text-xs font-mono px-3 py-1 rounded bg-yellow-900 text-yellow-200 status-pulse";

            // 1. Package
            const packRes = await fetch('/run/package', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            });
            const packData = await packRes.json();
            log(packData.message);

            // 2. Submit & Get Links
            log("Pushing to remote...");
            const pushRes = await fetch('/run/submit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({repo, version})
            });
            const pushData = await pushRes.json();
            
            if(pushData.status === "ok") {
                log("Deployment Successful!", "text-green-400");
                status.innerText = "LIVE";
                status.className = "text-xs font-mono px-3 py-1 rounded bg-green-900 text-green-200";
                
                // Show URL
                document.getElementById('cdn-url').innerText = pushData.cdn_url;
                successCard.classList.remove('hidden');
            } else {
                log("Error: " + pushData.message, "text-red-500");
                status.innerText = "FAILED";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_PAGE)

@app.route('/download')
def download():
    return send_file("dist/index.js", as_attachment=True)

@app.route('/run/<stage>', methods=['POST'])
def run_stage(stage):
    data = request.json
    try:
        if stage == 'package':
            raw = data['code']
            # Cleanly extract code (if user pastes script tags or just raw JS)
            js_content = re.sub(r'<script.*?>|</script>', '', raw, flags=re.DOTALL)
            
            # Auto-wrap in IIFE Namespace
            final_js = f"window.Vista = (function() {{\n{js_content}\n return this; \n}}).call({{}});"
            
            if not os.path.exists("dist"): os.makedirs("dist")
            with open("dist/index.js", "w") as f: f.write(final_js)
            return jsonify({"status": "ok", "message": "JS Compiled into /dist/index.js"})

        elif stage == 'submit':
            repo_raw = data['repo']
            version = data['version']
            
            # Clean Repo URL for CDN generation
            # Handles: git@github.com:user/repo.git OR https://github.com/user/repo
            clean_repo = repo_raw.replace("git@github.com:", "").replace("https://github.com/", "").replace(".git", "")
            cdn_url = f"https://cdn.jsdelivr.net/gh/{clean_repo}@{version}/dist/index.js"

            # Git Commands
            if not os.path.exists(".git"): subprocess.run(["git", "init"])
            subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", repo_raw])
            subprocess.run(["git", "add", "."])
            subprocess.run(["git", "commit", "-m", f"VISTA-DEPLOY: {version}"])
            subprocess.run(["git", "tag", "-a", version, "-m", "Release"])
            
            push = subprocess.run(["git", "push", "origin", "master", "--tags", "--force"], capture_output=True, text=True)
            
            if push.returncode == 0:
                return jsonify({
                    "status": "ok", 
                    "cdn_url": cdn_url,
                    "message": "Pushed to GitHub successfully."
                })
            else:
                return jsonify({"status": "error", "message": push.stderr})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
