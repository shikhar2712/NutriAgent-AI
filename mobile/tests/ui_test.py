"""End-to-end UI test: serves the built web assets, mocks an Ollama server, drives the app in a phone-sized
Chromium and saves screenshots. Fails on any uncaught JS error / console error.

    python3 tests/ui_test.py [shots_dir]
"""
import http.server, json, os, pathlib, socketserver, sys, threading, time, functools

ROOT = pathlib.Path(__file__).resolve().parents[1]
WWW = ROOT / "build" / "assets" / "www"          # staged by build.sh (includes data/nin_food_data.json)
PDF = ROOT.parent / "sample_blood_test_report.pdf"
SHOTS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/nutri_shots"); SHOTS.mkdir(parents=True, exist_ok=True)

# ---- mock Ollama --------------------------------------------------------------------------------------------
GEN_LOG = []
class Ollama(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj, code=200):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Headers", "*"); self.send_header("Access-Control-Allow-Methods", "*"); self.end_headers()
    def do_GET(self):
        if self.path == "/api/tags": self._send({"models": [{"name": "qwen2.5:7b"}, {"name": "qwen2.5:14b"}]})
        else: self._send({"error": "nf"}, 404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        GEN_LOG.append(body); time.sleep(0.6)
        sysmsg = body.get("system", "")
        if "Auditor" in sysmsg: txt = "### 1. Audit Verdict\n- **Safety & Compliance Score**: 92/100\n### 3. Doctor Brief\n- Mock AI doctor brief."
        elif "Diagnostic" in sysmsg: txt = "### Mock AI analysis\n**Executive summary**: mock analysis from the AI."
        elif "Dietitian" in sysmsg: txt = "### Mock AI dietitian notes\n- Eat more dal."
        elif "Consultant" in sysmsg: txt = "Mock AI consultant answer about your report."
        elif "general-purpose" in sysmsg: txt = "Mock plain LLM answer."
        else: txt = "Mock NutriAgent writing layer answer using the numbers provided."
        self._send({"response": txt})

def serve(handler, port):
    class T(socketserver.ThreadingTCPServer): allow_reuse_address = True; daemon_threads = True
    srv = T(("127.0.0.1", port), handler); threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def view_text(pg):
    return pg.inner_text('#view')

# ---- test ---------------------------------------------------------------------------------------------------
def main():
    from playwright.sync_api import sync_playwright
    serve(functools.partial(Quiet, directory=str(WWW)), 8811); serve(Ollama, 11999)
    errors, fails = [], []
    def check(cond, msg):
        print(("PASS " if cond else "FAIL ") + msg)
        if not cond: fails.append(msg)

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append("pageerror: %s" % e))
        pg.on("console", lambda m: errors.append("console.%s: %s" % (m.type, m.text)) if m.type == "error" else None)
        shot = lambda n: pg.screenshot(path=str(SHOTS / (n + ".png")))
        view = lambda: pg.inner_text("#view")

        pg.goto("http://127.0.0.1:8811/index.html"); pg.wait_for_selector(".hero")
        check("Turn your blood test" in view(), "home renders hero"); shot("01_home")
        check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal overflow on home")

        # ---- sample report -> intake sheet
        pg.click("text=Try the sample report"); pg.wait_for_selector("#sheet.on"); pg.wait_for_timeout(400)
        check("Lab report recognised" in pg.inner_text("#sheet"), "intake sheet recognises sample"); shot("02_intake")
        vals = pg.eval_on_selector_all("#sheet input[type=number]", "els => els.map(e => e.value)")
        check(vals[:3] == ["52", "86.5", "175"], "intake prefilled age/weight/height: %s" % vals)
        pg.click("text=Analyse my report"); pg.wait_for_selector("#pipeline"); pg.wait_for_timeout(700); shot("03_pipeline")
        pg.wait_for_selector(".rtabs", timeout=30000); pg.wait_for_timeout(500)
        check("Robert Vance" in view(), "report shows patient"); shot("04_overview")
        check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal overflow on report")

        tab = lambda t: (pg.click(".rtab:text-is('%s')" % t), pg.wait_for_timeout(350))
        tab("Biomarkers"); check("Fasting Blood Glucose" in view(), "biomarkers listed"); shot("05_biomarkers")
        pg.click("text=Out of range"); pg.wait_for_timeout(250); check("Serum Sodium" not in view(), "abnormal filter hides normal markers"); shot("06_biomarkers_abnormal")
        tab("Meal plan"); check("kcal planned" in view(), "meal plan day card"); shot("07_plan")
        pg.click(".day >> nth=2"); pg.wait_for_timeout(250); check("Day 3" in view(), "day switch works"); shot("08_plan_day3")
        tab("Doctor brief"); check("plan self-check" in view().lower(), "audit card"); shot("09_brief")
        tab("Ask"); pg.click("text=Can I eat rice?"); pg.wait_for_timeout(700)
        txt = view(); check("Rice" in txt and ("not advised" in txt), "offline Q&A flags rice for prediabetic: %s" % txt[-260:].replace("\n", " ")); shot("10_chat")
        tab("Export"); check("Share full report" in view(), "export actions"); shot("11_export")

        # ---- ask without report
        pg.click("#nav button:nth-child(3)"); pg.wait_for_selector("textarea")
        pg.click("text=I have gout and kidney issues, what foods are safe?"); pg.wait_for_timeout(900)
        check("Hyperuricemia" in view() and "Renal" in view(), "ask: gout+renal conditions detected"); shot("12_ask")
        check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal overflow on ask")

        # ---- settings + AI path against the mock
        pg.click("#nav button:nth-child(4)"); pg.wait_for_timeout(300); shot("13_settings")
        pg.click(".switch"); pg.wait_for_timeout(200)
        pg.fill("input[placeholder^='http']", "http://127.0.0.1:11999"); pg.dispatch_event("input[placeholder^='http']", "change")
        pg.click("text=Test connection"); pg.wait_for_selector(".testres.ok", timeout=8000); shot("14_settings_ai_ok")
        check("Connected" in view(), "AI connection test succeeds")
        pg.click("#nav button:nth-child(3)"); pg.wait_for_selector("textarea")
        n0 = len(GEN_LOG)
        pg.click("text=I have prediabetes and high cholesterol, what should I eat?"); pg.wait_for_selector("text=✦ AI · qwen2.5:7b", timeout=15000); pg.wait_for_timeout(300)
        check("Mock NutriAgent writing layer" in view(), "AI answer rendered"); check(len(GEN_LOG) == n0 + 1, "exactly one LLM call for ask")
        p = GEN_LOG[-1]["prompt"]; check("STRICTLY AVOID" in p and "kcal/day" in p, "ask prompt carries engine numbers"); shot("15_ask_ai")
        pg.click("text=Compare: plain AI vs NutriAgent"); pg.click("text=Ask the plain AI the same question"); pg.wait_for_selector("text=Mock plain LLM answer", timeout=8000); shot("16_compare")

        # full pipeline with AI
        pg.click("#nav button:nth-child(1)"); pg.wait_for_selector(".hero"); n0 = len(GEN_LOG)
        pg.click("text=Try the sample report"); pg.wait_for_selector("#sheet.on"); pg.wait_for_timeout(400); pg.click("text=Analyse my report")
        pg.wait_for_selector("#pipeline"); pg.wait_for_timeout(1200); shot("17_pipeline_ai")
        pg.wait_for_selector(".rtabs", timeout=40000); pg.wait_for_timeout(400)
        check(len(GEN_LOG) == n0 + 3, "pipeline made 3 LLM calls (got %d)" % (len(GEN_LOG) - n0))
        check("Mock AI analysis" in view(), "AI analysis shown"); tab("Doctor brief"); check("AI self-assessed: 92/100" in view(), "AI score parsed and labelled"); shot("18_brief_ai")
        check("Mock AI doctor brief" in view(), "AI doctor brief shown")

        # ---- real PDF upload through the file input (pdf.js in the browser)
        pg.click("#nav button:nth-child(1)"); pg.wait_for_selector(".hero")
        pg.set_input_files("#file", str(PDF)); pg.wait_for_selector("#sheet.on", timeout=20000); pg.wait_for_selector("text=Check your details", timeout=20000); pg.wait_for_timeout(400)
        t = pg.inner_text("#sheet"); check("Lab report recognised" in t and "18 biomarkers" in t, "real PDF parsed in-browser: %s" % t[:160].replace("\n", " ")); shot("19_pdf_intake")
        pg.click("#sheet .btn.primary"); pg.wait_for_selector(".rtabs", timeout=40000)

        # ---- PDF error paths: password-protected and image-only PDFs
        import subprocess
        errdir = SHOTS / "pdf_errors"; subprocess.run([sys.executable, str(ROOT / "tests" / "pdf_make_error_cases.py"), str(errdir)], check=True, capture_output=True)
        pg.click("#nav button:nth-child(1)"); pg.wait_for_selector(".hero")
        pg.set_input_files("#file", str(errdir / "encrypted.pdf")); pg.wait_for_selector("text=Password-protected PDF", timeout=20000); shot("25_pdf_encrypted")
        check("Remove the password" in pg.inner_text("#sheet"), "encrypted PDF -> friendly password message"); pg.click("#sheet >> text=Describe my health instead"); pg.wait_for_timeout(500)
        pg.click("#nav button:nth-child(1)"); pg.wait_for_selector(".hero")
        pg.set_input_files("#file", str(errdir / "scanned.pdf")); pg.wait_for_selector("text=This PDF has no text layer", timeout=20000); shot("26_pdf_scanned")
        check("scanned image" in pg.inner_text("#sheet"), "scanned PDF -> friendly no-text-layer message"); pg.click("#sheet >> text=Choose another PDF"); pg.wait_for_timeout(300)

        # ---- dark mode + small phone
        pg.click("#nav button:nth-child(4)"); pg.click("text=Dark"); pg.wait_for_timeout(300); shot("20_settings_dark")
        pg.click("#nav button:nth-child(2)"); pg.wait_for_timeout(300); shot("21_report_dark"); pg.click(".rtab:text-is('Meal plan')"); pg.wait_for_timeout(300); shot("22_plan_dark")
        pg.set_viewport_size({"width": 320, "height": 640}); pg.click(".rtab:text-is('Biomarkers')"); pg.wait_for_timeout(300)
        check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal overflow at 320px"); shot("23_small")

        # ---- simulated native bridge (what MainActivity injects as window.Native): http / share / theme + Skip-AI cancel
        ctx2 = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx2.add_init_script("""
          window.__calls = []; window.__shared = null; window.__theme = null;
          window.Native = {
            http(id, method, url, body, t) { window.__calls.push(method + ' ' + url);
              fetch(url, { method, body: body || undefined, headers: body ? {'Content-Type':'application/json'} : undefined })
                .then(async r => { const tx = await r.text(); setTimeout(() => window.__nativeCb(id, r.ok, r.ok ? tx : 'HTTP ' + r.status + ': ' + tx), 0); })
                .catch(e => window.__nativeCb(id, false, String(e))); },
            share(t, x) { window.__shared = { t, x }; },
            theme(d, b) { window.__theme = { d, b }; },\n            isNight() { return !!window.__night; } };
          localStorage.setItem('na.settings', JSON.stringify({ aiEnabled: true, url: 'http://127.0.0.1:11999', model: 'qwen2.5:7b', timeout: 60, diet: 'Vegetarian', allergies: ['Tree Nuts & Peanuts'], activity: 'Light', theme: 'light' }));
        """)
        q = ctx2.new_page(); q.on("pageerror", lambda e: errors.append("pageerror(native): %s" % e))
        q.goto("http://127.0.0.1:8811/index.html"); q.wait_for_selector(".hero"); q.wait_for_selector("text=AI connected", timeout=8000)
        check(any("GET http://127.0.0.1:11999/api/tags" in c for c in q.evaluate("window.__calls")), "native bridge used for /api/tags")
        check(q.evaluate("window.__theme") is not None and q.evaluate("window.__theme.b") == "#F4F7FB", "Native.theme called with light bar colour")
        q.click("text=Try the sample report"); q.wait_for_selector("#sheet.on"); q.wait_for_timeout(400)
        check("Vegetarian" in q.eval_on_selector("#sheet select", "e => e.value"), "intake pre-fills saved diet")
        q.click("text=Analyse my report"); q.wait_for_selector("text=Skip AI, use built-in engine"); q.wait_for_timeout(900)
        q.click("text=Skip AI, use built-in engine"); q.wait_for_selector(".rtabs", timeout=30000); q.wait_for_timeout(300)
        gens = [c for c in q.evaluate("window.__calls") if "/api/generate" in c]
        check(len(gens) <= 2, "Skip AI stopped further LLM calls (%d generate calls)" % len(gens))
        check("built-in engine" in view_text(q).lower() or "Built-in engine" in q.inner_text("#view"), "built-in engine used after skip")
        q.click(".rtab:text-is('Meal plan')"); q.wait_for_timeout(300)
        t = q.inner_text("#view").lower()
        check("allergens: tree nuts & peanuts" in t, "plan shows allergen caution"); check("upma" not in t and "poha" not in t and "chicken" not in t and "egg" not in t, "vegetarian + nut-free plan on Day 1")
        q.click(".rtab:text-is('Export')"); q.click("text=Share full report"); q.wait_for_timeout(200)
        check(q.evaluate("window.__shared && window.__shared.x.length") > 500, "Native.share received the report text"); q.screenshot(path=str(SHOTS / "24_native_export.png"))
        q.evaluate("window.__night = true"); q.click("#nav button:nth-child(4)"); q.click(".seg button:text-is('System')"); q.wait_for_timeout(300)
        check(q.evaluate("document.documentElement.dataset.theme") == "dark" and q.evaluate("window.__theme.d") is True, "System theme follows Native.isNight() (dark)")
        q.evaluate("window.__night = false; NutriApp.applyTheme()"); check(q.evaluate("document.documentElement.dataset.theme") == "light", "System theme flips back to light on config change")
        ctx2.close()
        br.close()

    real = [e for e in errors if "favicon" not in e]
    for e in real: print("JSERR", e)
    check(not real, "no JS errors / console errors (%d)" % len(real))
    print("\n%d failure(s)" % len(fails)); sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
