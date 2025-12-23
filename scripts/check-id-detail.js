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
        range: 'hcl_clips!A:C'
    });
    const rows = res.data.values;
    const target = 'MjtlxjhpfoE';
    const row = rows.find(r => r[0] === target);
    if (row) {
        console.log(`Video ID: ${row[0]}`);
        console.log(`Title: ${row[1]}`);
        console.log(`Date: ${row[2]}`);
    } else {
        console.log('Not found');
    }
}
check();
