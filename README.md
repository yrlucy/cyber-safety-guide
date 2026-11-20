資安防護行動指南
版本：2026-11-20。繁體中文、零外部依賴的靜態網站。主檔案為 `index.html`。
本機使用
雙擊 index.html，可在瀏覽器預覽。檢查表以本機 localStorage 保存；若瀏覽器停用此功能，請使用「下載我的檢查結果」。
部署 GitHub Pages
在 GitHub 建立公開 repository，如 `cyber-safety-guide`。
上傳 `index.html`（放在儲存庫根目錄）。
開啟 Settings > Pages > Build and deployment > Source: Deploy from a branch，Branch: main，Folder: /(root)，Save。
網址通常為 `https://<帳號>.github.io/cyber-safety-guide/`。
後續更新：讓 GPT 修改 index.html，重新上傳同名檔案並 Commit changes。請妥善保留版本備份。
修改位置
資安事件：搜尋 `id="news"`，新增或修改 `article class="card news"`。
風險分類：搜尋 `id="risks"`。
防護指南：搜尋 `id="guides"`。
檢查事項：在 JavaScript 的 `const groups=` 陣列修改。
異常應變：在 JavaScript 的 `const incidents=` 物件修改。
文字、主題顏色：CSS 的 `:root` 與頁面段落。
內容維護原則
新增新聞須標示事件日期、報導日期、來源連結，清楚區分推測與已證實資訊。
不應直接將新聞中的數字合併相加，避免同一事件重複統計。
不要將個人帳號、密碼、卡號、API key 放入網站原始碼。
檢查結果僅在各位訪客的裝置保存，不會同步到其他設備，也不是安全性診斷。
修改檢查表時若刪除或更動項目順序，可能影響舊版 localStorage 對應關係；建議修改 `key='cyber-guide-v1'` 版本名稱來重置進度，或改採穩定 ID。
