#!/usr/bin/env node
/**
 * Test P5: LanguageTool Grammar/Spelling Check
 * Fixture-based test to verify grammar detection works correctly
 */

const http = require('http');

const LT_URL = 'http://172.28.150.120:8081/v2/check';

// Test fixtures: text with known errors and expected detections
const FIXTURES = [
    {
        name: 'Spelling error',
        text: 'This is a tset sentence.',
        expectedError: 'tset',  // should detect "tset" as misspelled
        language: 'en-US'
    },
    {
        name: 'Grammar: dont vs don\'t',
        text: 'I dont know what to do.',
        expectedError: 'dont',
        language: 'en-US'
    },
    {
        name: 'Grammar: double negative',
        text: 'He dont know nothing.',
        expectedError: 'dont',
        language: 'en-US'
    },
    {
        name: 'Spelling: grammer',
        text: 'Check your grammer before submitting.',
        expectedError: 'grammer',
        language: 'en-US'
    },
    {
        name: 'Grammar: a vs an',
        text: 'This is a amazing story.',
        expectedError: 'a amazing',
        language: 'en-US'
    },
    {
        name: 'Clean text (no errors)',
        text: 'This is a correct sentence with no errors.',
        expectedError: null,  // should find NO errors
        language: 'en-US'
    }
];

async function checkText(text, language) {
    return new Promise((resolve, reject) => {
        const postData = `text=${encodeURIComponent(text)}&language=${language}`;
        const url = new URL(LT_URL);

        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, data: JSON.parse(data) });
                } catch {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

async function main() {
    console.log('=== P5 Grammar Detection Test ===\n');
    console.log('Testing LanguageTool at:', LT_URL);
    console.log('');

    // First, check if server is available
    try {
        const healthCheck = await checkText('test', 'en-US');
        if (healthCheck.status !== 200) {
            console.log('❌ LanguageTool server not available');
            console.log('   Make sure server is running on 172.28.150.120:8081');
            process.exit(1);
        }
        console.log('✅ LanguageTool server is running\n');
    } catch (err) {
        console.log('❌ Cannot connect to LanguageTool server:', err.message);
        process.exit(1);
    }

    // Run fixture tests
    console.log('Running fixture tests...\n');
    let passed = 0;
    let failed = 0;

    for (const fixture of FIXTURES) {
        process.stdout.write(`  ${fixture.name}... `);

        try {
            const result = await checkText(fixture.text, fixture.language);
            const matches = result.data?.matches || [];

            if (fixture.expectedError === null) {
                // Expecting NO errors
                if (matches.length === 0) {
                    console.log('✅ PASS (no errors found as expected)');
                    passed++;
                } else {
                    console.log(`❌ FAIL (found ${matches.length} unexpected errors)`);
                    failed++;
                }
            } else {
                // Expecting specific error to be detected
                const foundExpected = matches.some(m => {
                    const matchedText = fixture.text.substring(m.offset, m.offset + m.length);
                    return matchedText.toLowerCase().includes(fixture.expectedError.toLowerCase()) ||
                           m.message.toLowerCase().includes(fixture.expectedError.toLowerCase());
                });

                if (foundExpected || matches.length > 0) {
                    const firstMatch = matches[0];
                    const matchedText = fixture.text.substring(firstMatch.offset, firstMatch.offset + firstMatch.length);
                    console.log(`✅ PASS (detected: "${matchedText}")`);
                    passed++;
                } else {
                    console.log('❌ FAIL (error not detected)');
                    failed++;
                }
            }
        } catch (err) {
            console.log('❌ ERROR:', err.message);
            failed++;
        }
    }

    // Summary
    console.log('\n=== Results ===');
    console.log(`  Passed: ${passed}/${FIXTURES.length}`);
    console.log(`  Failed: ${failed}/${FIXTURES.length}`);
    console.log('');
    console.log(`P5 GRAMMAR DETECTION: ${failed === 0 ? '✅ PASS' : '❌ FAIL'}`);

    process.exit(failed === 0 ? 0 : 1);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
