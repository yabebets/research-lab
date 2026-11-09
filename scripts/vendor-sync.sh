#!/usr/bin/env bash
# 上流スキルの取り込み・更新。vendor/manifest.tsv の各行について
#   1) 上流を .cache/upstream/<repo> に clone / fetch
#   2) git subtree split で src_path だけの履歴を切り出す
#   3) 初回は subtree add、2回目以降は subtree pull（--squash は使わない）
# 使い方: scripts/vendor-sync.sh [name ...]   （name を省くと全部）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/.cache/upstream"
mkdir -p "$CACHE"
cd "$ROOT"

if [ -n "$(git status --porcelain -- vendor)" ]; then
  echo "vendor/ に未コミットの変更があります。先にコミットか破棄をしてください。" >&2
  exit 1
fi

fetched=" "
only=("$@")

while IFS=$'\t' read -r name url branch src dest; do
  [[ -z "${name:-}" || "$name" == \#* ]] && continue
  if [ ${#only[@]} -gt 0 ] && [[ ! " ${only[*]} " =~ " $name " ]]; then continue; fi
  repo="$CACHE/$(basename "$url" .git)"
  if [[ "$fetched" != *" $repo "* ]]; then
    if [ -d "$repo/.git" ]; then
      git -C "$repo" fetch -q origin "$branch"
      git -C "$repo" checkout -q -B "$branch" "origin/$branch"
    else
      git clone -q --branch "$branch" "$url" "$repo"
    fi
    fetched="$fetched$repo "
  fi
  echo "== $name: $src → $dest"
  sha="$(git -C "$repo" subtree split -q --prefix="$src" "$branch")"
  git -C "$repo" branch -f "rl-split/$name" "$sha" >/dev/null
  upstream_head="$(git -C "$repo" rev-parse --short "$branch")"
  if [ -d "$dest" ]; then
    git subtree pull -q --prefix="$dest" "$repo" "rl-split/$name" \
      -m "vendor: update $name from $(basename "$url" .git)@$upstream_head" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  else
    git subtree add -q --prefix="$dest" "$repo" "rl-split/$name" \
      -m "vendor: add $name from $(basename "$url" .git)@$upstream_head ($src)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  fi
done < vendor/manifest.tsv

echo "完了。続けて scripts/build-index.py で vendor/INDEX.md を作り直してください。"
