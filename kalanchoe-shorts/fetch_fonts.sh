#!/bin/sh
# HANDOFF.md「フォント」節の4ファイルを fonts/ に取得する（いずれも SIL OFL）
set -e
cd "$(dirname "$0")"
mkdir -p fonts
base=https://raw.githubusercontent.com/google/fonts/main/ofl
curl -sSfL --retry 3 -o fonts/ShipporiMinchoB1-ExtraBold.ttf "$base/shipporiminchob1/ShipporiMinchoB1-ExtraBold.ttf"
curl -sSfL --retry 3 -o fonts/ZenKakuGothicNew-Medium.ttf   "$base/zenkakugothicnew/ZenKakuGothicNew-Medium.ttf"
curl -sSfL --retry 3 -o fonts/ZenKakuGothicNew-Bold.ttf     "$base/zenkakugothicnew/ZenKakuGothicNew-Bold.ttf"
curl -sSfL --retry 3 -o "fonts/Oxanium[wght].ttf"           "$base/oxanium/Oxanium%5Bwght%5D.ttf"
ls -l fonts
