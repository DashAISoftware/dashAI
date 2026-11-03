#!/usr/bin/env bash
# Sign, package, notarize and staple the macOS build of dashAI.
#
# Usage: installer/macos/sign_and_notarize.sh <path/to/dashAI.app> <output.dmg>
#
# Required environment variables (GitHub Actions secrets):
#   MACOS_CERTIFICATE_P12_BASE64  Developer ID Application cert + private key (.p12, base64)
#   MACOS_CERTIFICATE_PASSWORD    Password used when exporting the .p12
#   MACOS_SIGNING_IDENTITY        e.g. "Developer ID Application: Name (TEAMID)"
#   APPLE_API_KEY_ID              App Store Connect API key ID
#   APPLE_API_KEY_P8              Contents of the AuthKey_<id>.p8 file
#
# Optional:
#   APPLE_ISSUER_ID               Only for Team API keys; individual keys have
#                                 no issuer and notarytool must not receive one
#
# Written for the stock macOS /bin/bash (3.2): no mapfile, no assoc arrays.

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <path/to/dashAI.app> <output.dmg>" >&2
    exit 2
fi

APP_PATH="$1"
DMG_PATH="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENTITLEMENTS="$SCRIPT_DIR/entitlements.plist"

for var in MACOS_CERTIFICATE_P12_BASE64 MACOS_CERTIFICATE_PASSWORD \
    MACOS_SIGNING_IDENTITY APPLE_API_KEY_ID APPLE_API_KEY_P8; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: environment variable $var is not set" >&2
        exit 1
    fi
done

if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: app bundle not found: $APP_PATH" >&2
    exit 1
fi

WORK_DIR="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/dashai-sign.XXXXXX")"
KEYCHAIN_PATH="$WORK_DIR/signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -base64 32)"
CERT_PATH="$WORK_DIR/certificate.p12"
API_KEY_PATH="$WORK_DIR/AuthKey_${APPLE_API_KEY_ID}.p8"

# Remember the user keychain search list so cleanup can restore it.
ORIGINAL_KEYCHAINS=()
while IFS= read -r line; do
    line="$(echo "$line" | sed -e 's/^[[:space:]]*"//' -e 's/"[[:space:]]*$//')"
    [ -n "$line" ] && ORIGINAL_KEYCHAINS+=("$line")
done < <(security list-keychains -d user)

cleanup() {
    echo "==> Cleaning up temporary keychain and credentials"
    security list-keychains -d user -s ${ORIGINAL_KEYCHAINS[@]+"${ORIGINAL_KEYCHAINS[@]}"} || true
    security delete-keychain "$KEYCHAIN_PATH" 2>/dev/null || true
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# ------------------------------------------------------------------
# 1. Temporary keychain with the Developer ID certificate
# ------------------------------------------------------------------
echo "==> Creating temporary keychain"
security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
# Auto-lock after 6h, enough for a full build + notarization.
security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"

echo "==> Importing signing certificate"
printf '%s' "$MACOS_CERTIFICATE_P12_BASE64" | base64 --decode > "$CERT_PATH"
security import "$CERT_PATH" -k "$KEYCHAIN_PATH" -f pkcs12 \
    -P "$MACOS_CERTIFICATE_PASSWORD" -T /usr/bin/codesign -T /usr/bin/security
# The .p12 exported from Keychain Access holds only the leaf certificate.
# Without Apple's intermediate CA the identity is "not valid" and codesign
# refuses it, so import the intermediate explicitly.
curl -fsSL -o "$WORK_DIR/DeveloperIDG2CA.cer" \
    https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer
security import "$WORK_DIR/DeveloperIDG2CA.cer" -k "$KEYCHAIN_PATH"
# Let codesign use the key without an interactive access prompt.
security set-key-partition-list -S apple-tool:,apple:,codesign: -s \
    -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH" > /dev/null
security list-keychains -d user -s "$KEYCHAIN_PATH" \
    ${ORIGINAL_KEYCHAINS[@]+"${ORIGINAL_KEYCHAINS[@]}"}

if ! security find-identity -v -p codesigning "$KEYCHAIN_PATH" \
    | grep -qF "$MACOS_SIGNING_IDENTITY"; then
    echo "ERROR: identity '$MACOS_SIGNING_IDENTITY' not usable from the keychain." >&2
    echo "Identities found:" >&2
    security find-identity -v -p codesigning "$KEYCHAIN_PATH" >&2
    exit 1
fi

CODESIGN_ARGS=(--force --timestamp --options runtime
    --sign "$MACOS_SIGNING_IDENTITY" --keychain "$KEYCHAIN_PATH")

# ------------------------------------------------------------------
# 2. Sign every Mach-O inside the bundle, then the bundle itself
# ------------------------------------------------------------------
# Inside-out signing instead of --deep (deprecated for signing). Candidates
# are .so/.dylib files and anything executable; `file` keeps only real
# Mach-O binaries so scripts and data with the x bit are skipped. Order
# between plain files does not matter, so they are signed in parallel; only
# the outer bundle has to come last.
echo "==> Collecting Mach-O binaries inside $APP_PATH"
BINARIES_LIST="$WORK_DIR/binaries.txt"
find "$APP_PATH/Contents" -type f \
    \( -name '*.so' -o -name '*.dylib' -o -perm -u+x \) -print0 \
    | xargs -0 file -N -F $'\t' \
    | awk -F $'\t' '$2 ~ /Mach-O/ { print $1 }' > "$BINARIES_LIST"
echo "    $(wc -l < "$BINARIES_LIST" | tr -d ' ') binaries to sign"

echo "==> Signing inner binaries"
tr '\n' '\0' < "$BINARIES_LIST" \
    | xargs -0 -n 25 -P 4 codesign "${CODESIGN_ARGS[@]}" \
        --entitlements "$ENTITLEMENTS"

echo "==> Signing app bundle"
codesign "${CODESIGN_ARGS[@]}" --entitlements "$ENTITLEMENTS" "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

# ------------------------------------------------------------------
# 3. Build and sign the DMG
# ------------------------------------------------------------------
echo "==> Creating DMG"
rm -f "$DMG_PATH"
create-dmg \
    --volname "dashAI Installer" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --app-drop-link 600 185 \
    --hide-extension "$(basename "$APP_PATH")" \
    --no-internet-enable \
    "$DMG_PATH" \
    "$APP_PATH"

echo "==> Signing DMG"
codesign --force --timestamp --sign "$MACOS_SIGNING_IDENTITY" \
    --keychain "$KEYCHAIN_PATH" "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"

# ------------------------------------------------------------------
# 4. Notarize and staple
# ------------------------------------------------------------------
printf '%s' "$APPLE_API_KEY_P8" > "$API_KEY_PATH"
chmod 600 "$API_KEY_PATH"
NOTARY_AUTH=(--key "$API_KEY_PATH" --key-id "$APPLE_API_KEY_ID")
if [ -n "${APPLE_ISSUER_ID:-}" ]; then
    NOTARY_AUTH+=(--issuer "$APPLE_ISSUER_ID")
fi

echo "==> Submitting DMG for notarization (this can take several minutes)"
RESULT_JSON="$WORK_DIR/notary-result.json"
xcrun notarytool submit "$DMG_PATH" "${NOTARY_AUTH[@]}" \
    --wait --timeout 2h --output-format json > "$RESULT_JSON" || true
cat "$RESULT_JSON"; echo

STATUS="$(plutil -extract status raw "$RESULT_JSON" 2>/dev/null || echo unknown)"
SUBMISSION_ID="$(plutil -extract id raw "$RESULT_JSON" 2>/dev/null || echo "")"

if [ "$STATUS" != "Accepted" ]; then
    echo "ERROR: notarization status is '$STATUS'" >&2
    if [ -n "$SUBMISSION_ID" ]; then
        echo "==> Notarization log for $SUBMISSION_ID" >&2
        xcrun notarytool log "$SUBMISSION_ID" "${NOTARY_AUTH[@]}" >&2 || true
    fi
    exit 1
fi

echo "==> Stapling notarization ticket"
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"

echo "==> Gatekeeper assessment"
spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG_PATH"

echo "==> Done: $DMG_PATH is signed, notarized and stapled"
