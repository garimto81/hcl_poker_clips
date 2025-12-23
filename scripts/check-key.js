import 'dotenv/config';

console.log('--- Key Debug ---');
const key = process.env.GOOGLE_PRIVATE_KEY;
console.log('Key defined:', !!key);
if (key) {
    console.log('Key length:', key.length);
    console.log('First 20 chars:', key.substring(0, 20));
    console.log('Last 20 chars:', key.substring(key.length - 20));

    const cleaned = key.replace(/^"(.*)"$/, '$1').replace(/\\n/g, '\n');
    console.log('Cleaned length:', cleaned.length);
    console.log('Cleaned first 20:', cleaned.substring(0, 20));
}
