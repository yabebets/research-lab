# programs/

研究プログラム（系統・幹・論文の並び）を置く。1 プログラム = 1 フォルダ（`program.md` と `program.yaml`）。
中身は git の管理外（このリポジトリは公開なので、出願や事業の計画を含むプログラムは入れない）。必要なら各フォルダを別の非公開リポジトリにする。

- `rl program new <name>`：作る
- `rl program link <program> <paper_id> <project>`：論文とプロジェクトを紐づける（両方の台帳を書く）
- `rl program status [name]`：系統ごとに論文と紐づいたプロジェクトの段階・確認ポイント・依存の待ちを表示
- `rl program readme [name]`：program.md の状況の枠を書き直す
- `rl new <project> --program <name> --paper <ID>`：作るときに紐づける
