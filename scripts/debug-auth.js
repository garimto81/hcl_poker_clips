import 'dotenv/config';
import { google } from 'googleapis';

async function debugAuth() {
    console.log('--- Auth Debug Start ---');
    console.log('Sheet ID:', process.env.GOOGLE_SHEET_ID);
    console.log('YouTube Key starts with:', process.env.YOUTUBE_API_KEY?.substring(0, 5));
    console.log('Service Email:', process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL);

    const youtube = google.youtube({ version: 'v3', auth: process.env.YOUTUBE_API_KEY });
    const auth = new google.auth.JWT(
        process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
        null,
        process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
        ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/youtube.readonly']
    );

    try {
        console.log('Testing YouTube API...');
        const ytRes = await youtube.playlists.list({
            channelId: 'UCOYjui_6iH-ab2MDG6uooiQ',
            part: 'snippet',
            maxResults: 1
        });
        console.log('✅ YouTube API OK. Playlist count:', ytRes.data.items.length);
    } catch (e) {
        console.error('❌ YouTube API Failed:', e.message);
    }

    try {
        console.log('Testing Sheets API...');
        const sheets = google.sheets({ version: 'v4', auth });
        const ssres = await sheets.spreadsheets.get({
            spreadsheetId: process.env.GOOGLE_SHEET_ID
        });
        console.log('✅ Sheets API OK. Title:', ssres.data.properties.title);
    } catch (e) {
        console.error('❌ Sheets API Failed:', e.message);
        console.log('Hint: Make sure the service account email is added as an Editor to the sheet.');
    }
}

debugAuth();
