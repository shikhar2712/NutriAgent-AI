# NutriAgent mobile (Android APK)

A standalone Android port of NutriAgent. The Python clinical engine (extraction, Mifflin-St Jeor, protocol stacking,
NIN food tables, Indian 7-day plan, audit) runs **on the phone** in JavaScript; the lab PDF is read on the phone with a
bundled pdf.js. A Qwen model on your own Ollama server is **optional** and only adds written analysis and open-ended chat.

`dist/NutriAgent.apk` - install it by copying it to the phone and opening it (allow "install unknown apps").
Package `com.nutriagent.app`, Android 7+ (API 24) with an up-to-date Android System WebView (pdf.js 3.11 and modern CSS need it), ~0.5 MB, one permission (INTERNET, only used for the Ollama address you enter).
It is signed with a debug key that `build.sh` generates on the first build (`debug.keystore`, not committed). To update an installed copy, rebuild with the same keystore, otherwise Android treats it as a different app.

## Using it
1. **Home > Upload lab report (PDF)** or **Try the sample report**. Check the pre-filled details, tap **Analyse**.
2. Report tabs: Overview (flags, macro targets), Biomarkers (range bars), Meal plan (7 days, swipe, grocery list),
   Doctor brief (plan self-check + shareable memo), Ask (chat about your report), Export (share text/JSON).
3. **Ask** tab: no report needed; describe conditions/height/weight in a sentence.
4. **Settings > AI server** (optional): on the computer run `ollama pull qwen2.5:7b`, then `OLLAMA_HOST=0.0.0.0 ollama serve`,
   put the phone on the same Wi-Fi and enter `http://<computer-ip>:11434`. Without it every screen still works.

## Layout
- `web/` - the app (HTML/CSS/JS, no framework, no CDN). `js/engine.js` is the port of `extractor.py`,
  `deterministic_nutrition.py`, `indian_foods.py`, `general_intake.py`. `js/agents.js` has the ported LLM prompts and the
  offline builders. `js/pdftext.js` + `vendor/pdfjs` read PDFs.
- `android/` - ~200-line native shell (WebView, asset server on a secure origin, PDF file chooser, Ollama HTTP bridge, share).
- `build.sh` - Gradle-free build: aapt2 > javac > d8 > zipalign > apksigner. Needs JDK 17, Android SDK platform-34 + d8.jar
  (`ANDROID_SDK`, default `/opt/android-sdk`) and native `aapt2 zipalign apksigner` on PATH (apt `aapt zipalign apksigner`
  on arm64 Linux, where the SDK's x86-64 build-tools do not run).
- `tests/` - see below. `tools/gen_sample.py` regenerates the sample report from `app.py`.

## Tests
```
python3 tests/gen_fixtures.py && node tests/parity.test.js   # JS engine == Python originals (1033 checks)
node tests/safety.test.js                                      # allergen / diet / flag exclusions over the 7-day plan
python3 tests/pdf_verify.py                                    # pdf.js text -> same biomarkers as pdfplumber (3 PDFs)
./build.sh && python3 tests/ui_test.py [shots_dir]             # headless phone-size UI run with a mock Ollama + simulated native bridge
```
`tests/DEVIATIONS.md` lists every intentional difference from the Python code.

## Known limits
- I have not run it on a physical device or emulator. The native shell is verified by compilation, APK structure and
  signature checks, a Java quoting test and a simulated bridge, not by a real WebView.
- Scanned (image-only) PDFs have no text layer; there is no OCR.
- Allergen filtering is by food name, plus Poha/Upma for nut allergy. Check recipes yourself.
- Educational tool, not a medical device. The "plan self-check" verifies the plan against its own rules, not clinically.
