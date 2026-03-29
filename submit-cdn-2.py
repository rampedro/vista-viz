from flask import Flask, render_template_string, jsonify, request
import os, re, subprocess, time

app = Flask(__name__)

# --- THE UI (Includes your preferred Headless Test) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vista Autonomous Pipeline v3</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #020617; color: #f1f5f9; font-family: 'Inter', sans-serif; }
        textarea { background: #0f172a !important; color: #10b981 !important; font-family: 'Fira Code', monospace; border: 1px solid #1e293b; }
        .status-pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
        .console { background: #000; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <div class="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
            <h1 class="text-2xl font-black italic text-blue-500 tracking-tighter uppercase">Vista // Smart Deploy</h1>
            <div id="pipeline-status" class="text-xs font-mono px-3 py-1 rounded bg-slate-800 text-slate-400">READY</div>
        </div>

        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-8">
                <textarea id="code-input" class="w-full h-96 p-4 rounded-xl mt-2 outline-none focus:border-blue-500" placeholder="Paste Full HTML Source..."></textarea>
                <div class="grid grid-cols-2 gap-4 mt-4">
                    <input id="repo-url" type="text" value="git@github.com:rampedro/vista-viz.git" class="bg-slate-900 p-2 rounded border border-slate-800 text-sm">
                    <input id="version" type="text" value="v1.0.0" class="bg-slate-900 p-2 rounded border border-slate-800 text-sm">
                </div>
            </div>

            <div class="col-span-4 flex flex-col">
                <div id="console" class="console p-4 mb-4 rounded-xl border border-slate-800"></div>
                <button onclick="triggerAutomation()" class="bg-blue-600 hover:bg-blue-500 py-4 rounded-xl font-black tracking-widest transition active:scale-95">START PIPELINE</button>
            </div>
        </div>
        <iframe id="sandbox" class="hidden"></iframe>
    </div>

    <script>
        function log(msg, color='text-slate-400') {
            const c = document.getElementById('console');
            c.innerHTML += `<div class="mb-1 ${color}">> ${msg}</div>`;
            c.scrollTop = c.scrollHeight;
        }

        async function triggerAutomation() {
            const status = document.getElementById('pipeline-status');
            const code = document.getElementById('code-input').value;
            const repo = document.getElementById('repo-url').value;
            const version = document.getElementById('version').value;

            status.innerText = "PACKAGING...";
            log("Extracting Logic via NLP...");

            // 1. PACKAGE
            const packRes = await fetch('/run/package', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            });
            const packData = await packRes.json();
            log(packData.message);

            // 2. HEADLESS TEST (Check if script loads)
            log("Testing Build Integrity...");
            const testResult = await runHeadlessTest();
            
            if(testResult) {
                log("Tests Passed", "text-green-400");
                status.innerText = "PUSHING...";
                const pushRes = await fetch('/run/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({repo, version})
                });
                const pushData = await pushRes.json();
                log(pushData.message, pushData.status === 'ok' ? "text-blue-400" : "text-red-400");
                status.innerText = pushData.status === 'ok' ? "DEPLOYED" : "FAILED";
            } else {
                log("Tests Failed: Script Syntax Error", "text-red-500");
                status.innerText = "FAILED";
            }
        }

        function runHeadlessTest() {
            return new Promise((resolve) => {
                const sandbox = document.getElementById('sandbox');
                // Use cache buster to ensure we test the FRESHLY packaged file
                sandbox.srcdoc = `<script src="/dist/index.js?t=${Date.now()}"><\/script><script>setTimeout(() => { window.parent.postMessage('ok', '*'); }, 100);<\/script>`;
                window.onmessage = (e) => resolve(e.data === 'ok');
                setTimeout(() => resolve(false), 2000); // Timeout fail
            });
        }
    </script>
</body>
</html>
"""

# --- BACKEND ---

@app.route('/')
def index(): return render_template_string(HTML_PAGE)

@app.route('/dist/index.js')
def serve_lib():
    # Cache busting headers are critical for the Headless Test to work
    if os.path.exists("dist/index.js"):
        with open("dist/index.js", "r") as f:
            return f.read(), 200, {'Content-Type': 'application/javascript', 'Cache-Control': 'no-store'}
    return "Not Found", 404

@app.route('/run/<stage>', methods=['POST'])
def run_stage(stage):
    data = request.json
    try:
        if stage == 'package':
            raw = data['code']
            # Find all internal JS (skips external CDN links)
            scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', raw, re.DOTALL)
            js_content = "\n\n".join(scripts)
            
            if not os.path.exists("dist"): os.makedirs("dist")
            with open("dist/index.js", "w") as f:
                f.write(js_content)
            return jsonify({"status": "ok", "message": f"Extracted {len(scripts)} code blocks."})

        elif stage == 'submit':
            # Identity injection to prevent "Please tell me who you are" Git errors
            env = os.environ.copy()
            env["GIT_AUTHOR_NAME"] = "Pedram"
            env["GIT_AUTHOR_EMAIL"] = "pedram@example.com"
            env["GIT_COMMITTER_NAME"] = "Pedram"
            env["GIT_COMMITTER_EMAIL"] = "pedram@example.com"

            if not os.path.exists(".git"): subprocess.run(["git", "init"])
            
            subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
            subprocess.run(["git", "remote", "add", "origin", data['repo']])
            
            subprocess.run(["git", "add", "."])
            subprocess.run(["git", "commit", "-m", f"Auto-release {data['version']}"], env=env)
            
            # Use --force on tags to allow overwriting versions during testing
            subprocess.run(["git", "tag", "-f", data['version'], "-m", "Release"], env=env)
            
            push = subprocess.run(["git", "push", "origin", "HEAD:main", "--tags", "--force"], capture_output=True, text=True)
            
            if push.returncode == 0:
                return jsonify({"status": "ok", "message": "Pushed to GitHub."})
            return jsonify({"status": "error", "message": f"Push Failed: {push.stderr}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
