from flask import Flask, render_template_string, jsonify, request, send_file
import os, re, subprocess, time

app = Flask(__name__)

# --- THE UI (Modern Automation Dashboard) ---
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
            <div id="pipeline-status" class="text-xs font-mono px-3 py-1 rounded bg-slate-800 text-slate-400">READY</div>
        </div>

        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-8">
                <div class="mb-4">
                    <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Library Source (JS)</label>
                    <textarea id="code-input" class="w-full h-80 p-4 rounded-xl mt-2 outline-none focus:border-blue-500" placeholder="function myLib() { console.log('active'); }"></textarea>
                </div>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="text-[10px] font-bold text-slate-500 uppercase">GitHub Repo (SSH/HTTPS)</label>
                        <input id="repo-url" type="text" placeholder="git@github.com:user/repo.git" class="w-full bg-slate-900 p-2 rounded border border-slate-800 text-sm mt-1">
                    </div>
                    <div>
                        <label class="text-[10px] font-bold text-slate-500 uppercase">Version/Tag</label>
                        <input id="version" type="text" placeholder="v1.0.0" class="w-full bg-slate-900 p-2 rounded border border-slate-800 text-sm mt-1">
                    </div>
                </div>

                <div id="success-card" class="hidden mt-6 p-4 bg-blue-900/20 border border-blue-500/50 rounded-xl">
                    <h3 class="text-blue-400 font-bold text-sm mb-2">🚀 DEPLOYMENT COMPLETE</h3>
                    <div class="text-xs space-y-2">
                        <p class="text-slate-400">JSDelivr CDN URL:</p>
                        <code id="cdn-url" class="block bg-black p-2 rounded text-blue-300 break-all select-all"></code>
                        <a href="/download" class="inline-block mt-2 text-blue-400 underline font-bold">Download index.js Locally</a>
                    </div>
                </div>
            </div>

            <div class="col-span-4 flex flex-col">
                <div class="mb-4">
                    <label class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Pipeline Logs</label>
                    <div id="console" class="console p-4 mt-2 rounded-xl border border-slate-800">
                        <div class="text-slate-600">// System Initialized</div>
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

            if(!code || !repo || !version) { log("Error: All fields required", "text-red-500"); return; }
            successCard.classList.add('hidden');

            status.innerText = "EXECUTING...";
            status.className = "text-xs font-mono px-3 py-1 rounded bg-yellow-900 text-yellow-200 status-pulse";

            // Stage 1: Build/Package
            log("Compiling package...");
            const packRes = await fetch('/run/package', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            });
            const packData = await packRes.json();
            log(packData.message);

            // Stage 2: Git Ops
            log("Running Git push to remote...");
            const pushRes = await fetch('/run/submit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({repo, version})
            });
            const pushData = await pushRes.json();
            
            if(pushData.status === "ok") {
                log("Successfully deployed to CDN", "text-green-400");
                status.innerText = "SUCCESS";
                status.className = "text-xs font-mono px-3 py-1 rounded bg-green-900 text-green-200";
                document.getElementById('cdn-url').innerText = pushData.cdn_url;
                successCard.classList.remove('hidden');
            } else {
                log("Git Error: " + pushData.message, "text-red-500");
                status.innerText = "ERROR";
                status.className = "text-xs font-mono px-3 py-1 rounded bg-red-900 text-red-200";
            }
        }
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---

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
            # Remove any html script tags if present
            js_body = re.sub(r'<script.*?>|</script>', '', raw, flags=re.DOTALL)
            
            # Wrap in a scope
            final_js = f"/* Vista Auto-Build */\nwindow.Vista = (function() {{\n{js_body}\n return this; \n}}).call({{}});"
            
            if not os.path.exists("dist"): os.makedirs("dist")
            with open("dist/index.js", "w") as f: f.write(final_js)
            
            # Create a change file to guarantee a commit is possible
            with open("dist/build.log", "w") as f:
                f.write(f"Build: {time.ctime()}")

            return jsonify({"status": "ok", "message": "Package generated in /dist"})

        elif stage == 'submit':
            repo_raw = data['repo']
            version = data['version']

            # Git Config / Initialization
            if not os.path.exists(".git"):
                subprocess.run(["git", "init"])
                subprocess.run(["git", "checkout", "-b", "main"])

            # Sync Remote
            subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", repo_raw])

            # Virtual Identity (Crucial for servers without global git config)
            env = os.environ.copy()
            env["GIT_AUTHOR_NAME"] = "Vista CI"
            env["GIT_AUTHOR_EMAIL"] = "ci@vista.io"
            env["GIT_COMMITTER_NAME"] = "Vista CI"
            env["GIT_COMMITTER_EMAIL"] = "ci@vista.io"

            # Commit & Tag
            subprocess.run(["git", "add", "."], env=env)
            subprocess.run(["git", "commit", "-m", f"Release {version}"], env=env)
            subprocess.run(["git", "tag", "-a", version, "-m", "Release"], env=env)

            # Push HEAD to remote 'main' branch
            push = subprocess.run(
                ["git", "push", "origin", "HEAD:main", "--tags", "--force"], 
                capture_output=True, text=True, env=env
            )

            if push.returncode == 0:
                # Build the CDN Link
                # regex to extract user/repo from git@github.com:user/repo.git or https://...
                parts = re.search(r"github\.com[:/](.+?/.+?)(?:\.git|$)", repo_raw)
                repo_path = parts.group(1) if parts else "user/repo"
                cdn_url = f"https://cdn.jsdelivr.net/gh/{repo_path}@{version}/dist/index.js"
                
                return jsonify({"status": "ok", "cdn_url": cdn_url})
            else:
                return jsonify({"status": "error", "message": push.stderr or push.stdout})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
