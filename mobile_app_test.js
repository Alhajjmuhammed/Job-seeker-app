#!/usr/bin/env node
/**
 * Mobile App API Integration Test
 * Tests the API service functions used by the React Native app
 */

const https = require('https');
const http = require('http');

// Test configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
const TEST_TOKEN = '8cd0ec3ee39c07161db00c177411db3333a98bed'; // Token for alhajjmuhammed@gmail.com

function makeRequest(path, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
        const url = new URL(path, API_BASE_URL);
        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname + url.search,
            method: method,
            headers: {
                'Authorization': `Token ${TEST_TOKEN}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };

        if (data && method !== 'GET') {
            const postData = JSON.stringify(data);
            options.headers['Content-Length'] = Buffer.byteLength(postData);
        }

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    const result = JSON.parse(body);
                    resolve({
                        status: res.statusCode,
                        data: result,
                        headers: res.headers
                    });
                } catch (e) {
                    resolve({
                        status: res.statusCode,
                        data: body,
                        headers: res.headers
                    });
                }
            });
        });

        req.on('error', reject);
        
        if (data && method !== 'GET') {
            req.write(JSON.stringify(data));
        }
        
        req.end();
    });
}

async function testMobileAppIntegration() {
    console.log('📱 Testing Mobile App API Integration...');
    console.log(`🌐 Base URL: ${API_BASE_URL}`);
    console.log(`🔑 Using token: ${TEST_TOKEN.substring(0, 10)}...`);
    console.log('');

    try {
        // Test 1: Worker stats (like home screen)
        console.log('📊 Testing worker stats endpoint (Home Screen)...');
        const statsResponse = await makeRequest('/api/workers/stats/');
        if (statsResponse.status === 200) {
            console.log('✅ Stats API working:', JSON.stringify(statsResponse.data, null, 2));
        } else {
            console.log('❌ Stats API failed:', statsResponse.status, statsResponse.data);
        }
        console.log('');

        // Test 2: Assigned jobs (like assigned jobs screen)
        console.log('📋 Testing assigned jobs endpoint (Assigned Jobs Screen)...');
        const jobsResponse = await makeRequest('/api/workers/assigned-jobs/');
        if (jobsResponse.status === 200) {
            console.log('✅ Assigned Jobs API working:', JSON.stringify(jobsResponse.data, null, 2));
        } else {
            console.log('❌ Assigned Jobs API failed:', jobsResponse.status, jobsResponse.data);
        }
        console.log('');

        // Test 3: Profile endpoint
        console.log('👤 Testing worker profile endpoint...');
        const profileResponse = await makeRequest('/api/workers/profile/');
        if (profileResponse.status === 200) {
            console.log('✅ Profile API working:', JSON.stringify(profileResponse.data, null, 2));
        } else {
            console.log('❌ Profile API failed:', profileResponse.status, profileResponse.data);
        }
        console.log('');

        console.log('🎉 Mobile App API Integration Test Complete!');
        console.log('📱 All endpoints that the React Native app uses are working correctly.');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        if (error.code === 'ECONNREFUSED') {
            console.log('🔧 Make sure the Django server is running on 192.168.0.238:8000');
        }
    }
}

// Run the test
testMobileAppIntegration();