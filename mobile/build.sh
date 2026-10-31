#!/usr/bin/env bash
# Builds dist/NutriAgent.apk without Gradle: aapt2 -> javac -> d8 -> zipalign -> apksigner.
# Needs: JDK 17, Android platform 34 jar + d8.jar (SDK at $ANDROID_SDK), and native aapt2/zipalign/apksigner on PATH.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="${ANDROID_SDK:-/opt/android-sdk}"
JAR="$SDK/platforms/android-34/android.jar"
D8="$SDK/build-tools/34.0.0/lib/d8.jar"
B="$HERE/build"; OUT="$HERE/dist"
rm -rf "$B"; mkdir -p "$B"/{gen,classes,assets,res} "$OUT"

cp -r "$HERE/android/res/." "$B/res/"
python3 "$HERE/make_icons.py" "$B/res"
python3 "$HERE/tools/gen_sample.py" >/dev/null
cp -r "$HERE/web" "$B/assets/www"
mkdir -p "$B/assets/www/data"
cp "$HERE/../nin_food_data.json" "$B/assets/www/data/nin_food_data.json"

aapt2 compile --dir "$B/res" -o "$B/res.zip"
aapt2 link -o "$B/base.apk" -I "$JAR" --manifest "$HERE/android/AndroidManifest.xml" \
  --java "$B/gen" -A "$B/assets" --min-sdk-version 24 --target-sdk-version 34 \
  --version-code 1 --version-name 1.0 "$B/res.zip"

javac --release 8 -nowarn -d "$B/classes" -cp "$JAR" \
  $(find "$HERE/android/src" "$B/gen" -name '*.java') 2>&1 | grep -v '^Note:\|warning: \[options\]' || true
java -cp "$D8" com.android.tools.r8.D8 --release --min-api 24 --lib "$JAR" --output "$B" \
  $(find "$B/classes" -name '*.class')

(cd "$B" && zip -q -u base.apk classes.dex)
zipalign -p -f 4 "$B/base.apk" "$B/aligned.apk"

KS="$HERE/debug.keystore"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storepass nutriagent -keypass nutriagent -alias nutriagent \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=NutriAgent" >/dev/null 2>&1
fi
apksigner sign --ks "$KS" --ks-pass pass:nutriagent --key-pass pass:nutriagent \
  --out "$OUT/NutriAgent.apk" "$B/aligned.apk"
apksigner verify --verbose "$OUT/NutriAgent.apk" | head -3
ls -la "$OUT/NutriAgent.apk"
