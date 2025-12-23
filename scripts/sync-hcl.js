import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_DIR = path.join(__dirname, '../data');
const STATE_FILE = path.join(DATA_DIR, 'sync-state.json');
const SPREADSHEET_ID = process.env.GOOGLE_SHEET_ID;
const CHANNEL_ID = 'UCOYjui_6iH-ab2MDG6uooiQ';
const TAB_NAME = 'hcl_clips';

async function smartSync() {
    console.log(`🚀 [Smart Sync] ${new Date().toLocaleString()} 시작`);

    try {
        if (!SPREADSHEET_ID) throw new Error('GOOGLE_SHEET_ID missing');

        // 0. 상태 로드 (ETag 기억용)
        if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
        let state = { playlistEtags: {} };
        if (fs.existsSync(STATE_FILE)) {
            state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
        }

        const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
        let privateKey = process.env.GOOGLE_PRIVATE_KEY;
        if (!email || !privateKey) throw new Error('Auth env vars missing');
        privateKey = privateKey.replace(/^"(.*)"$/, '$1').replace(/\\n/g, '\n');

        const auth = new google.auth.JWT({
            email,
            key: privateKey,
            scopes: [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/youtube.readonly'
            ]
        });

        await auth.authorize();
        const sheets = google.sheets({ version: 'v4', auth });
        const youtube = google.youtube({ version: 'v3', auth });

        // 1. 시트 분석
        console.log('🔍 시트 분석 중...');
        const ss = await sheets.spreadsheets.get({ spreadsheetId: SPREADSHEET_ID });
        const targetSheet = ss.data.sheets.find(s => s.properties.title.toLowerCase() === TAB_NAME.toLowerCase());
        if (!targetSheet) throw new Error(`${TAB_NAME} 탭을 찾을 수 없습니다.`);

        const actualTabName = targetSheet.properties.title;
        const sheetId = targetSheet.properties.sheetId;

        const rangeRes = await sheets.spreadsheets.values.get({
            spreadsheetId: SPREADSHEET_ID,
            range: `${actualTabName}!A1:P2500`
        });
        const rows = rangeRes.data.values || [];
        const headers = rows[0] || [];
        const videoIndex = new Map();
        rows.forEach((row, idx) => { if (idx > 0 && row[0]) videoIndex.set(row[0], idx + 1); });

        // 2. 유튜브 플레이리스트 로드 (ETag 체크)
        console.log('📡 유튜브 플레이리스트 로드 중...');
        const plRes = await youtube.playlists.list({
            channelId: CHANNEL_ID,
            part: 'snippet',
            maxResults: 50
        });

        const headerMap = headers.slice(3).reduce((acc, h, i) => { acc[h] = i + 3; return acc; }, {});

        // ETag가 변경되었거나 시트에 없는 플레이리스트만 동기화 대상
        const targetPlaylists = plRes.data.items.filter(pl => {
            const hasColumn = headerMap[pl.snippet.title] !== undefined;
            const etagChanged = state.playlistEtags[pl.id] !== pl.etag;
            return hasColumn && etagChanged;
        });

        if (targetPlaylists.length === 0) {
            console.log('✅ 모든 플레이리스트가 최신 상태입니다. (ETag 일치)');
            // 시간만 업데이트하고 종료 가능
        } else {
            console.log(`🔗 동기화 대상 플레이리스트 ${targetPlaylists.length}개 발견 (내용 변경됨)`);

            const videoMap = new Map();
            for (const pl of targetPlaylists) {
                console.log(`   - [${pl.snippet.title}] 분석 중...`);
                let nextPageToken = null;
                do {
                    const itemsRes = await youtube.playlistItems.list({
                        playlistId: pl.id,
                        part: 'snippet,contentDetails',
                        maxResults: 50,
                        pageToken: nextPageToken
                    });
                    for (const item of itemsRes.data.items) {
                        const vId = item.contentDetails.videoId;
                        if (!videoMap.has(vId)) {
                            videoMap.set(vId, {
                                title: item.snippet.title,
                                date: item.snippet.publishedAt,
                                playlists: new Set()
                            });
                        }
                        videoMap.get(vId).playlists.add(pl.snippet.title);
                    }
                    nextPageToken = itemsRes.data.nextPageToken;
                } while (nextPageToken);

                // 성공적으로 읽었으면 ETag 업데이트
                state.playlistEtags[pl.id] = pl.etag;
            }

            // 4. 변경 사항 적용
            const newVideos = [];
            const cellUpdates = [];

            for (const [vId, data] of videoMap) {
                const rowNum = videoIndex.get(vId);
                if (rowNum) {
                    for (const plTitle of data.playlists) {
                        const colIdx = headerMap[plTitle];
                        const colLetter = String.fromCharCode(65 + colIdx);
                        cellUpdates.push({
                            range: `${actualTabName}!${colLetter}${rowNum}`,
                            values: [[true]]
                        });
                    }
                } else {
                    newVideos.push({ vId, ...data });
                }
            }

            if (cellUpdates.length > 0) {
                console.log(`🆙 ${cellUpdates.length}개 항목 업데이트...`);
                for (let i = 0; i < cellUpdates.length; i += 500) {
                    await sheets.spreadsheets.values.batchUpdate({
                        spreadsheetId: SPREADSHEET_ID,
                        requestBody: { data: cellUpdates.slice(i, i + 500), valueInputOption: 'USER_ENTERED' }
                    });
                }
            }

            if (newVideos.length > 0) {
                console.log(`✨ ${newVideos.length}개 신규 영상 추가 (상단 삽입)...`);
                newVideos.sort((a, b) => b.date.localeCompare(a.date));
                const insertRows = newVideos.map(v => {
                    const row = [v.vId, `=HYPERLINK("https://www.youtube.com/watch?v=${v.vId}", "${v.title.replace(/"/g, '""')}")`, v.date];
                    headers.slice(3).forEach(h => row.push(v.playlists.has(h)));
                    return row;
                });

                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId: SPREADSHEET_ID,
                    requestBody: {
                        requests: [{ insertDimension: { range: { sheetId, dimension: 'ROWS', startIndex: 1, endIndex: 1 + insertRows.length } } }]
                    }
                });

                await sheets.spreadsheets.values.update({
                    spreadsheetId: SPREADSHEET_ID,
                    range: `${actualTabName}!A2`,
                    valueInputOption: 'USER_ENTERED',
                    requestBody: { values: insertRows }
                });

                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId: SPREADSHEET_ID,
                    requestBody: {
                        requests: [{
                            setDataValidation: {
                                range: { sheetId, startRowIndex: 1, endRowIndex: 1 + insertRows.length, startColumnIndex: 3, endColumnIndex: headers.length },
                                rule: { condition: { type: 'BOOLEAN' }, showCustomUi: true }
                            }
                        }]
                    }
                });
            }
        }

        // 5. 전체 시트 정렬 (신규 추가든 기존 업데이트든 항상 최신순으로)
        console.log('↕️ 시트 정렬 중 (최신순)...');
        await sheets.spreadsheets.batchUpdate({
            spreadsheetId: SPREADSHEET_ID,
            requestBody: {
                requests: [
                    {
                        sortRange: {
                            range: {
                                sheetId: sheetId,
                                startRowIndex: 1, // 헤더 제외
                                startColumnIndex: 0,
                                endColumnIndex: headers.length
                            },
                            sortSpecs: [
                                { dimensionIndex: 2, sortOrder: 'DESCENDING' } // Column C (Date)
                            ]
                        }
                    }
                ]
            }
        });

        // 6. 마지막 동기화 시간 기록
        fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
        console.log('✅ 스마트 동기화 완료!');
    } catch (error) {
        console.error('❌ 스마트 동기화 실패:', error.message);
    }
}

smartSync();
