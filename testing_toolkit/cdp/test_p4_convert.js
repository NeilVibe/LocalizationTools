#!/usr/bin/env node
/**
 * Test P4: File Conversions
 * Tests converting files between TXT/XML/Excel/TMX formats
 */

const http = require('http');

const API_BASE = 'http://localhost:8888';

async function request(method, path, body = null, token = null) {
    return new Promise((resolve, reject) => {
        const url = new URL(path, API_BASE);
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname + url.search,
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }

        const req = http.request(options, (res) => {
            let data = [];
            res.on('data', chunk => data.push(chunk));
            res.on('end', () => {
                const buffer = Buffer.concat(data);
                resolve({
                    status: res.statusCode,
                    headers: res.headers,
                    data: buffer,
                    size: buffer.length
                });
            });
        });

        req.on('error', reject);

        if (body) {
            req.write(JSON.stringify(body));
        }
        req.end();
    });
}

async function main() {
    console.log('=== P4 File Conversions Test ===\n');

    // Step 1: Login
    console.log('STEP 1: Login...');
    const loginRes = await request('POST', '/api/auth/login', {
        username: 'neil',
        password: 'test123'
    });

    if (loginRes.status !== 200) {
        console.log('  Login failed');
        process.exit(1);
    }

    const token = JSON.parse(loginRes.data.toString()).access_token;
    console.log('  Logged in successfully\n');

    // Step 2: Find files of different formats
    console.log('STEP 2: Find test files...');
    const projectsRes = await request('GET', '/api/ldm/projects', null, token);
    const projects = JSON.parse(projectsRes.data.toString());

    let txtFile = null;
    let xmlFile = null;

    for (const project of projects) {
        const filesRes = await request('GET', `/api/ldm/projects/${project.id}/files`, null, token);
        const files = JSON.parse(filesRes.data.toString());

        if (!txtFile) txtFile = files.find(f => f.format?.toLowerCase() === 'txt');
        if (!xmlFile) xmlFile = files.find(f => f.format?.toLowerCase() === 'xml');

        if (txtFile && xmlFile) break;
    }

    console.log('  TXT file:', txtFile ? `${txtFile.name} (ID: ${txtFile.id})` : 'Not found');
    console.log('  XML file:', xmlFile ? `${xmlFile.name} (ID: ${xmlFile.id})` : 'Not found');
    console.log('');

    const testResults = [];

    // Step 3: Test TXT conversions
    if (txtFile) {
        console.log('STEP 3: Test TXT conversions...');

        // TXT → Excel
        const toExcel = await request('GET', `/api/ldm/files/${txtFile.id}/convert?format=xlsx`, null, token);
        const excelOK = toExcel.status === 200 && toExcel.size > 0;
        console.log('  TXT → Excel:', excelOK ? `✅ PASS (${toExcel.size} bytes)` : `❌ FAIL (${toExcel.status})`);
        testResults.push({ test: 'TXT→Excel', pass: excelOK });

        // TXT → XML
        const toXml = await request('GET', `/api/ldm/files/${txtFile.id}/convert?format=xml`, null, token);
        const xmlOK = toXml.status === 200 && toXml.size > 0;
        console.log('  TXT → XML:', xmlOK ? `✅ PASS (${toXml.size} bytes)` : `❌ FAIL (${toXml.status})`);
        testResults.push({ test: 'TXT→XML', pass: xmlOK });

        // TXT → TMX
        const toTmx = await request('GET', `/api/ldm/files/${txtFile.id}/convert?format=tmx`, null, token);
        const tmxOK = toTmx.status === 200 && toTmx.size > 0;
        console.log('  TXT → TMX:', tmxOK ? `✅ PASS (${toTmx.size} bytes)` : `❌ FAIL (${toTmx.status})`);
        testResults.push({ test: 'TXT→TMX', pass: tmxOK });

        // TXT → TXT (should fail - same format)
        const toTxt = await request('GET', `/api/ldm/files/${txtFile.id}/convert?format=txt`, null, token);
        const sameFormatRejected = toTxt.status === 400;
        console.log('  TXT → TXT:', sameFormatRejected ? '✅ Correctly rejected (same format)' : '❌ Should reject');
        testResults.push({ test: 'TXT→TXT rejection', pass: sameFormatRejected });

        console.log('');
    }

    // Step 4: Test XML conversions
    if (xmlFile) {
        console.log('STEP 4: Test XML conversions...');

        // XML → Excel
        const toExcel = await request('GET', `/api/ldm/files/${xmlFile.id}/convert?format=xlsx`, null, token);
        const excelOK = toExcel.status === 200 && toExcel.size > 0;
        console.log('  XML → Excel:', excelOK ? `✅ PASS (${toExcel.size} bytes)` : `❌ FAIL (${toExcel.status})`);
        testResults.push({ test: 'XML→Excel', pass: excelOK });

        // XML → TMX
        const toTmx = await request('GET', `/api/ldm/files/${xmlFile.id}/convert?format=tmx`, null, token);
        const tmxOK = toTmx.status === 200 && toTmx.size > 0;
        console.log('  XML → TMX:', tmxOK ? `✅ PASS (${toTmx.size} bytes)` : `❌ FAIL (${toTmx.status})`);
        testResults.push({ test: 'XML→TMX', pass: tmxOK });

        // XML → TXT (should fail - StringID loss)
        const toTxt = await request('GET', `/api/ldm/files/${xmlFile.id}/convert?format=txt`, null, token);
        const txtRejected = toTxt.status === 400;
        console.log('  XML → TXT:', txtRejected ? '✅ Correctly rejected (StringID loss)' : '❌ Should reject');
        testResults.push({ test: 'XML→TXT rejection', pass: txtRejected });

        console.log('');
    }

    // Step 5: Test invalid format
    console.log('STEP 5: Test invalid format...');
    if (txtFile) {
        const invalidRes = await request('GET', `/api/ldm/files/${txtFile.id}/convert?format=invalid`, null, token);
        const invalidRejected = invalidRes.status === 422 || invalidRes.status === 400;
        console.log('  Invalid format:', invalidRejected ? '✅ Correctly rejected' : '❌ Should reject');
        testResults.push({ test: 'Invalid format rejection', pass: invalidRejected });
    }
    console.log('');

    // Summary
    console.log('=== P4 Conversion Test Results ===');
    const passed = testResults.filter(r => r.pass).length;
    const total = testResults.length;

    for (const r of testResults) {
        console.log(`  ${r.pass ? '✅' : '❌'} ${r.test}`);
    }

    console.log('');
    console.log(`P4 CONVERSIONS: ${passed === total ? '✅ PASS' : '❌ FAIL'} (${passed}/${total} tests)`);

    process.exit(passed === total ? 0 : 1);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
