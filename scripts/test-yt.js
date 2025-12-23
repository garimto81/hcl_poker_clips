import 'dotenv/config';
import { google } from 'googleapis';

async function test() {
    const youtube = google.youtube({ version: 'v3', auth: process.env.YOUTUBE_API_KEY });
    const res = await youtube.playlists.list({
        channelId: 'UCOYjui_6iH-ab2MDG6uooiQ',
        part: 'snippet,etag',
        maxResults: 5
    });
    console.log('Item 0:', JSON.stringify(res.data.items[0], null, 2));
}
test();
