import 'dotenv/config';
import { google } from 'googleapis';

async function check() {
    const auth = new google.auth.JWT({
        email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
        key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n'),
        scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly']
    });
    const sheets = google.sheets({ version: 'v4', auth });
    const res = await sheets.spreadsheets.values.get({
        spreadsheetId: process.env.GOOGLE_SHEET_ID,
        range: 'hcl_clips!A:A'
    });
    const ids = res.data.values.flat();
    const target = 'MjtlxjhpfoE';
    console.log(`Searching for ${target}...`);
    console.log(`Found: ${ids.includes(target)}`);
}
check();
