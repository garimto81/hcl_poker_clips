import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;
const SPREADSHEET_ID = process.env.GOOGLE_SHEET_ID;
const DATA_PATH = path.join(__dirname, '../public/data/videos.json');
const CHANNEL_ID = 'UCOYjui_6iH-ab2MDG6uooiQ';

async function syncVideoMatrix() {
    console.log('--- Video Matrix Sync (Official Google API) Started ---');

    try {
        if (!YOUTUBE_API_KEY) throw new Error('YOUTUBE_API_KEY is missing');
        const youtube = google.youtube({ version: 'v3', auth: YOUTUBE_API_KEY });

        // 1. Fetch from YouTube
        const plResponse = await youtube.playlists.list({
            channelId: CHANNEL_ID,
            part: 'snippet',
            maxResults: 50
        });

        const activePlaylists = plResponse.data.items.slice(0, 12).map(pl => ({
            id: pl.id,
            title: pl.snippet.title
        }));
        const playlistTitles = activePlaylists.map(pl => pl.title);

        const videoMap = new Map();
        for (const pl of activePlaylists) {
            let nextPageToken = null;
            do {
                const itemsResponse = await youtube.playlistItems.list({
                    playlistId: pl.id,
                    part: 'snippet,contentDetails',
                    maxResults: 50,
                    pageToken: nextPageToken
                });
                for (const item of itemsResponse.data.items) {
                    const videoId = item.contentDetails.videoId;
                    if (!videoMap.has(videoId)) {
                        videoMap.set(videoId, { id: videoId, title: item.snippet.title, publishedAt: item.snippet.publishedAt, playlists: {} });
                    }
                    videoMap.get(videoId).playlists[pl.title] = true;
                }
                nextPageToken = itemsResponse.data.nextPageToken;
            } while (nextPageToken);
        }
        const allVideos = Array.from(videoMap.values()).sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));

        // 2. Google Sheets Update via Official API
        if (SPREADSHEET_ID && process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL) {
            const auth = new google.auth.JWT(
                process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
                null,
                process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
                ['https://www.googleapis.com/auth/spreadsheets']
            );

            const sheets = google.sheets({ version: 'v4', auth });

            // Find or create sheet
            const ss = await sheets.spreadsheets.get({ spreadsheetId: SPREADSHEET_ID });
            let sheet = ss.data.sheets.find(s => s.properties.title === 'Video_Matrix');
            let sheetId;

            if (!sheet) {
                const res = await sheets.spreadsheets.batchUpdate({
                    spreadsheetId: SPREADSHEET_ID,
                    requestBody: { requests: [{ addSheet: { properties: { title: 'Video_Matrix' } } }] }
                });
                sheetId = res.data.replies[0].addSheet.properties.sheetId;
            } else {
                sheetId = sheet.properties.sheetId;
            }

            // Headers
            const headers = ['Video ID', 'Title', 'PublishedAt', ...playlistTitles];

            // Prepare Data Grid
            const rows = allVideos.map(v => {
                const values = [
                    v.id,
                    `=HYPERLINK("https://www.youtube.com/watch?v=${v.id}", "${v.title.replace(/"/g, '""')}")`,
                    v.publishedAt
                ];
                playlistTitles.forEach(t => values.push(v.playlists[t] ? true : false));
                return values;
            });

            const dataToSet = [headers, ...rows];

            // Update Values
            await sheets.spreadsheets.values.update({
                spreadsheetId: SPREADSHEET_ID,
                range: 'Video_Matrix!A1',
                valueInputOption: 'USER_ENTERED',
                requestBody: { values: dataToSet }
            });

            // Apply Checkboxes
            console.log('Applying real checkboxes via Official API...');
            await sheets.spreadsheets.batchUpdate({
                spreadsheetId: SPREADSHEET_ID,
                requestBody: {
                    requests: [
                        {
                            setDataValidation: {
                                range: {
                                    sheetId: sheetId,
                                    startRowIndex: 1,
                                    endRowIndex: dataToSet.length,
                                    startColumnIndex: 3,
                                    endColumnIndex: headers.length
                                },
                                rule: {
                                    condition: { type: 'BOOLEAN' },
                                    showCustomUi: true
                                }
                            }
                        }
                    ]
                }
            });
            console.log('Sheet sync complete with real checkboxes.');
        }

        fs.writeFileSync(DATA_PATH, JSON.stringify(allVideos, null, 2));
    } catch (error) {
        console.error('Final official sync error:', error.message);
    }
}

syncVideoMatrix();
