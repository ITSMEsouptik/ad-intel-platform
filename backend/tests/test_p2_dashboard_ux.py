"""
Tests for P2 UX Improvements: Dashboard redesign with pack_status and brand_name enrichment

Test coverage:
1. GET /api/campaign-briefs returns pack_status and brand_name fields
2. Different pack_status values: success, partial, running, failed, none
3. brand_name fallback when no pack exists
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestP2DashboardAPIEnrichment:
    """Tests for P2 Dashboard API - pack_status and brand_name enrichment"""

    @pytest.fixture(autouse=True)
    def setup_test_user(self):
        """Create test user and session for authenticated tests"""
        import subprocess
        result = subprocess.run([
            'mongosh', '--eval', f'''
            use('test_database');
            var userId = 'test-p2-api-{uuid.uuid4().hex[:8]}';
            var sessionToken = 'test_session_p2_api_{uuid.uuid4().hex[:12]}';
            db.users.insertOne({{
              user_id: userId,
              email: 'test.p2.api.' + Date.now() + '@example.com',
              name: 'P2 API Test User',
              picture: 'https://via.placeholder.com/150',
              created_at: new Date()
            }});
            db.user_sessions.insertOne({{
              user_id: userId,
              session_token: sessionToken,
              expires_at: new Date(Date.now() + 7*24*60*60*1000),
              created_at: new Date()
            }});
            print('SESSION:' + sessionToken);
            print('USERID:' + userId);
            '''
        ], capture_output=True, text=True)
        
        output = result.stdout
        self.session_token = None
        self.user_id = None
        for line in output.split('\n'):
            if line.startswith('SESSION:'):
                self.session_token = line.replace('SESSION:', '')
            elif line.startswith('USERID:'):
                self.user_id = line.replace('USERID:', '')
        
        yield
        
        # Cleanup
        if self.session_token:
            subprocess.run([
                'mongosh', '--eval', f'''
                use('test_database');
                db.users.deleteMany({{user_id: /test-p2-api/}});
                db.user_sessions.deleteMany({{session_token: /test_session_p2_api/}});
                db.campaign_briefs.deleteMany({{user_id: /test-p2-api/}});
                db.website_context_packs.deleteMany({{campaign_brief_id: /test-p2-/}});
                '''
            ], capture_output=True)

    def test_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'

    def test_campaign_briefs_list_unauthenticated_returns_401(self):
        """GET /api/campaign-briefs returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/campaign-briefs")
        assert response.status_code == 401

    def test_campaign_briefs_list_returns_pack_status_none_when_no_pack(self):
        """GET /api/campaign-briefs returns pack_status='none' when no pack exists"""
        # Create a brief
        headers = {"Authorization": f"Bearer {self.session_token}"}
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": f"test-p2-{uuid.uuid4().hex[:8]}.com", "country": "United States"},
            headers=headers
        )
        assert create_resp.status_code == 200
        brief_id = create_resp.json()['campaign_brief_id']
        
        # List briefs
        list_resp = requests.get(f"{BASE_URL}/api/campaign-briefs", headers=headers)
        assert list_resp.status_code == 200
        briefs = list_resp.json()
        
        # Find our brief
        our_brief = next((b for b in briefs if b['campaign_brief_id'] == brief_id), None)
        assert our_brief is not None
        assert our_brief.get('pack_status') == 'none'
        assert our_brief.get('brand_name') is None

    def test_campaign_briefs_list_returns_pack_status_success(self):
        """GET /api/campaign-briefs returns pack_status='success' when pack is success"""
        import subprocess
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        # Create brief
        brief_id = f"test-p2-{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": f"{brief_id}.com", "country": "United States"},
            headers=headers
        )
        assert create_resp.status_code == 200
        actual_brief_id = create_resp.json()['campaign_brief_id']
        
        # Create pack with status=success and brand_name
        subprocess.run([
            'mongosh', '--eval', f'''
            use('test_database');
            db.website_context_packs.insertOne({{
              website_context_pack_id: 'pack-{uuid.uuid4().hex[:8]}',
              campaign_brief_id: '{actual_brief_id}',
              status: 'success',
              step2: {{
                brand_summary: {{
                  name: 'Test Brand Success'
                }}
              }},
              created_at: new Date(),
              updated_at: new Date()
            }});
            '''
        ], capture_output=True)
        
        # List briefs
        list_resp = requests.get(f"{BASE_URL}/api/campaign-briefs", headers=headers)
        assert list_resp.status_code == 200
        briefs = list_resp.json()
        
        # Find our brief
        our_brief = next((b for b in briefs if b['campaign_brief_id'] == actual_brief_id), None)
        assert our_brief is not None
        assert our_brief.get('pack_status') == 'success'
        assert our_brief.get('brand_name') == 'Test Brand Success'

    def test_campaign_briefs_list_returns_pack_status_processing_for_running(self):
        """GET /api/campaign-briefs returns pack_status='processing' when pack is running"""
        import subprocess
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        # Create brief
        brief_id = f"test-p2-{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": f"{brief_id}.com", "country": "United States"},
            headers=headers
        )
        assert create_resp.status_code == 200
        actual_brief_id = create_resp.json()['campaign_brief_id']
        
        # Create pack with status=running
        subprocess.run([
            'mongosh', '--eval', f'''
            use('test_database');
            db.website_context_packs.insertOne({{
              website_context_pack_id: 'pack-{uuid.uuid4().hex[:8]}',
              campaign_brief_id: '{actual_brief_id}',
              status: 'running',
              step2: {{
                brand_summary: {{
                  name: 'Processing Brand'
                }}
              }},
              created_at: new Date(),
              updated_at: new Date()
            }});
            '''
        ], capture_output=True)
        
        # List briefs
        list_resp = requests.get(f"{BASE_URL}/api/campaign-briefs", headers=headers)
        assert list_resp.status_code == 200
        briefs = list_resp.json()
        
        # Find our brief
        our_brief = next((b for b in briefs if b['campaign_brief_id'] == actual_brief_id), None)
        assert our_brief is not None
        assert our_brief.get('pack_status') == 'processing'  # running maps to processing
        assert our_brief.get('brand_name') == 'Processing Brand'

    def test_campaign_briefs_list_returns_pack_status_failed(self):
        """GET /api/campaign-briefs returns pack_status='failed' when pack failed"""
        import subprocess
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        # Create brief
        brief_id = f"test-p2-{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": f"{brief_id}.com", "country": "Germany"},
            headers=headers
        )
        assert create_resp.status_code == 200
        actual_brief_id = create_resp.json()['campaign_brief_id']
        
        # Create pack with status=failed
        subprocess.run([
            'mongosh', '--eval', f'''
            use('test_database');
            db.website_context_packs.insertOne({{
              website_context_pack_id: 'pack-{uuid.uuid4().hex[:8]}',
              campaign_brief_id: '{actual_brief_id}',
              status: 'failed',
              step2: {{
                brand_summary: {{
                  name: 'Failed Brand'
                }}
              }},
              created_at: new Date(),
              updated_at: new Date()
            }});
            '''
        ], capture_output=True)
        
        # List briefs
        list_resp = requests.get(f"{BASE_URL}/api/campaign-briefs", headers=headers)
        assert list_resp.status_code == 200
        briefs = list_resp.json()
        
        # Find our brief
        our_brief = next((b for b in briefs if b['campaign_brief_id'] == actual_brief_id), None)
        assert our_brief is not None
        assert our_brief.get('pack_status') == 'failed'
        assert our_brief.get('brand_name') == 'Failed Brand'

    def test_campaign_briefs_list_returns_pack_status_partial(self):
        """GET /api/campaign-briefs returns pack_status='partial' when pack is partial"""
        import subprocess
        
        headers = {"Authorization": f"Bearer {self.session_token}"}
        
        # Create brief
        brief_id = f"test-p2-{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": f"{brief_id}.com", "country": "France"},
            headers=headers
        )
        assert create_resp.status_code == 200
        actual_brief_id = create_resp.json()['campaign_brief_id']
        
        # Create pack with status=partial
        subprocess.run([
            'mongosh', '--eval', f'''
            use('test_database');
            db.website_context_packs.insertOne({{
              website_context_pack_id: 'pack-{uuid.uuid4().hex[:8]}',
              campaign_brief_id: '{actual_brief_id}',
              status: 'partial',
              step2: {{
                brand_summary: {{
                  name: 'Partial Brand'
                }}
              }},
              created_at: new Date(),
              updated_at: new Date()
            }});
            '''
        ], capture_output=True)
        
        # List briefs
        list_resp = requests.get(f"{BASE_URL}/api/campaign-briefs", headers=headers)
        assert list_resp.status_code == 200
        briefs = list_resp.json()
        
        # Find our brief
        our_brief = next((b for b in briefs if b['campaign_brief_id'] == actual_brief_id), None)
        assert our_brief is not None
        assert our_brief.get('pack_status') == 'partial'
        assert our_brief.get('brand_name') == 'Partial Brand'


class TestWizardFlowAPI:
    """Test wizard flow API works correctly"""

    def test_create_campaign_brief_minimal_payload(self):
        """POST /api/campaign-briefs accepts minimal payload {website_url, country}"""
        response = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": "test-wizard-minimal.com", "country": "United States"}
        )
        assert response.status_code == 200
        data = response.json()
        assert 'campaign_brief_id' in data
        assert data['brand']['website_url'] == 'https://test-wizard-minimal.com'
        assert data['geo']['country'] == 'United States'
        # Check defaults
        assert data['goal']['primary_goal'] == 'bookings_leads'
        assert data['destination']['type'] == 'website'
        assert data['track'] == 'pilot'

    def test_get_campaign_brief_by_id(self):
        """GET /api/campaign-briefs/{id} returns correct brief"""
        # Create
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": "test-wizard-get.com", "country": "Canada"}
        )
        assert create_resp.status_code == 200
        brief_id = create_resp.json()['campaign_brief_id']
        
        # Get
        get_resp = requests.get(f"{BASE_URL}/api/campaign-briefs/{brief_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data['campaign_brief_id'] == brief_id
        assert data['geo']['country'] == 'Canada'

    def test_get_campaign_brief_not_found(self):
        """GET /api/campaign-briefs/{id} returns 404 for non-existent ID"""
        response = requests.get(f"{BASE_URL}/api/campaign-briefs/nonexistent-123")
        assert response.status_code == 404

    def test_start_orchestration(self):
        """POST /api/orchestrations/{id}/start creates orchestration"""
        # Create brief
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={"website_url": "test-orchestration-start.com", "country": "United States"}
        )
        assert create_resp.status_code == 200
        brief_id = create_resp.json()['campaign_brief_id']
        
        # Start orchestration
        orch_resp = requests.post(f"{BASE_URL}/api/orchestrations/{brief_id}/start")
        assert orch_resp.status_code == 200
        data = orch_resp.json()
        assert data['campaign_brief_id'] == brief_id
        assert 'orchestration_id' in data
        assert data['status'] == 'running'
