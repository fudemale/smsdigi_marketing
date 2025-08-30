#!/usr/bin/env python3
"""
SMS Marketing SaaS Backend Testing Suite
Tests all backend API endpoints and functionality
"""

import requests
import json
import uuid
from datetime import datetime
import sys
import os

# Get backend URL from environment
BACKEND_URL = "https://sms-engage.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_health_check(self):
        """Test the /api/health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy" and data.get("database") == "connected":
                    self.log_test("Health Check", True, "Server and database are healthy")
                    return True
                else:
                    self.log_test("Health Check", False, "Invalid health response format", data)
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        try:
            # Test preflight request
            headers = {
                'Origin': 'https://example.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = self.session.options(f"{self.base_url}/health", headers=headers, timeout=10)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if cors_headers['Access-Control-Allow-Origin'] == '*':
                self.log_test("CORS Headers", True, "CORS headers properly configured", cors_headers)
                return True
            else:
                self.log_test("CORS Headers", False, "CORS not properly configured", cors_headers)
                return False
                
        except Exception as e:
            self.log_test("CORS Headers", False, f"Error testing CORS: {str(e)}")
            return False
    
    def test_contact_form_submission(self):
        """Test POST /api/contact with complete contact form data"""
        try:
            # Test data with realistic information
            contact_data = {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@techcorp.com",
                "company": "TechCorp Solutions",
                "phone": "+1-555-0123",
                "message": "I'm interested in your SMS marketing platform for our e-commerce business. We send about 10,000 messages per month.",
                "plan_interest": "Professional"
            }
            
            response = self.session.post(
                f"{self.base_url}/contact",
                json=contact_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Verify all fields are returned
                required_fields = ['id', 'name', 'email', 'company', 'phone', 'message', 'plan_interest', 'created_at']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and data['email'] == contact_data['email']:
                    self.log_test("Contact Form Submission", True, "Contact form submitted successfully", 
                                {"contact_id": data.get('id'), "email": data.get('email')})
                    return True, data
                else:
                    self.log_test("Contact Form Submission", False, "Response missing required fields", 
                                {"missing": missing_fields, "response": data})
                    return False, None
            else:
                self.log_test("Contact Form Submission", False, f"HTTP {response.status_code}", response.text)
                return False, None
                
        except Exception as e:
            self.log_test("Contact Form Submission", False, f"Error: {str(e)}")
            return False, None
    
    def test_newsletter_subscription(self):
        """Test POST /api/newsletter with email subscription"""
        try:
            # Test data with realistic email
            newsletter_data = {
                "email": "marketing.updates@businesscorp.com"
            }
            
            response = self.session.post(
                f"{self.base_url}/newsletter",
                json=newsletter_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'email', 'created_at']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and data['email'] == newsletter_data['email']:
                    self.log_test("Newsletter Subscription", True, "Newsletter subscription successful",
                                {"subscriber_id": data.get('id'), "email": data.get('email')})
                    return True, data
                else:
                    self.log_test("Newsletter Subscription", False, "Response missing required fields",
                                {"missing": missing_fields, "response": data})
                    return False, None
            else:
                self.log_test("Newsletter Subscription", False, f"HTTP {response.status_code}", response.text)
                return False, None
                
        except Exception as e:
            self.log_test("Newsletter Subscription", False, f"Error: {str(e)}")
            return False, None
    
    def test_duplicate_newsletter_subscription(self):
        """Test duplicate newsletter subscription handling"""
        try:
            # Use the same email as previous test
            newsletter_data = {
                "email": "marketing.updates@businesscorp.com"
            }
            
            response = self.session.post(
                f"{self.base_url}/newsletter",
                json=newsletter_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 400:
                data = response.json()
                if "already subscribed" in data.get('detail', '').lower():
                    self.log_test("Duplicate Newsletter Subscription", True, "Duplicate subscription properly rejected")
                    return True
                else:
                    self.log_test("Duplicate Newsletter Subscription", False, "Wrong error message for duplicate", data)
                    return False
            else:
                self.log_test("Duplicate Newsletter Subscription", False, f"Expected 400, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Duplicate Newsletter Subscription", False, f"Error: {str(e)}")
            return False
    
    def test_invalid_data_submissions(self):
        """Test invalid data submission handling"""
        try:
            # Test invalid contact form (missing required fields)
            invalid_contact = {"name": ""}  # Missing email
            
            response = self.session.post(
                f"{self.base_url}/contact",
                json=invalid_contact,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            contact_validation_ok = response.status_code in [400, 422]  # Should reject invalid data
            
            # Test invalid newsletter (invalid email format)
            invalid_newsletter = {"email": "not-an-email"}
            
            response = self.session.post(
                f"{self.base_url}/newsletter",
                json=invalid_newsletter,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            newsletter_validation_ok = response.status_code in [400, 422]  # Should reject invalid email
            
            if contact_validation_ok and newsletter_validation_ok:
                self.log_test("Invalid Data Validation", True, "Invalid data properly rejected")
                return True
            else:
                self.log_test("Invalid Data Validation", False, 
                            f"Validation failed - Contact: {contact_validation_ok}, Newsletter: {newsletter_validation_ok}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Data Validation", False, f"Error: {str(e)}")
            return False
    
    def test_get_contacts(self):
        """Test GET /api/contacts to verify data storage"""
        try:
            response = self.session.get(f"{self.base_url}/contacts", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if we have at least one contact (from our previous test)
                    if len(data) > 0:
                        # Verify structure of first contact
                        contact = data[0]
                        required_fields = ['id', 'name', 'email', 'created_at']
                        missing_fields = [field for field in required_fields if field not in contact]
                        
                        if not missing_fields:
                            self.log_test("Get Contacts", True, f"Retrieved {len(data)} contacts successfully",
                                        {"count": len(data), "sample_contact_id": contact.get('id')})
                            return True
                        else:
                            self.log_test("Get Contacts", False, "Contact data missing required fields",
                                        {"missing": missing_fields})
                            return False
                    else:
                        self.log_test("Get Contacts", True, "No contacts found (empty database)")
                        return True
                else:
                    self.log_test("Get Contacts", False, "Response is not a list", {"type": type(data)})
                    return False
            else:
                self.log_test("Get Contacts", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Contacts", False, f"Error: {str(e)}")
            return False
    
    def test_get_subscribers(self):
        """Test GET /api/subscribers to verify data storage"""
        try:
            response = self.session.get(f"{self.base_url}/subscribers", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Check if we have at least one subscriber (from our previous test)
                    if len(data) > 0:
                        # Verify structure of first subscriber
                        subscriber = data[0]
                        required_fields = ['id', 'email', 'created_at']
                        missing_fields = [field for field in required_fields if field not in subscriber]
                        
                        if not missing_fields:
                            self.log_test("Get Subscribers", True, f"Retrieved {len(data)} subscribers successfully",
                                        {"count": len(data), "sample_subscriber_id": subscriber.get('id')})
                            return True
                        else:
                            self.log_test("Get Subscribers", False, "Subscriber data missing required fields",
                                        {"missing": missing_fields})
                            return False
                    else:
                        self.log_test("Get Subscribers", True, "No subscribers found (empty database)")
                        return True
                else:
                    self.log_test("Get Subscribers", False, "Response is not a list", {"type": type(data)})
                    return False
            else:
                self.log_test("Get Subscribers", False, f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Subscribers", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print(f"🚀 Starting SMS Marketing SaaS Backend Tests")
        print(f"📡 Testing backend at: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("CORS Headers", self.test_cors_headers),
            ("Contact Form Submission", self.test_contact_form_submission),
            ("Newsletter Subscription", self.test_newsletter_subscription),
            ("Duplicate Newsletter Subscription", self.test_duplicate_newsletter_subscription),
            ("Invalid Data Validation", self.test_invalid_data_submissions),
            ("Get Contacts", self.test_get_contacts),
            ("Get Subscribers", self.test_get_subscribers),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Test execution error: {str(e)}")
        
        print("=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend is working correctly.")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed. Check the details above.")
            return False
    
    def get_summary(self):
        """Get a summary of test results"""
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "0%",
            "results": self.test_results
        }
        
        return summary

def main():
    """Main test execution"""
    tester = BackendTester()
    success = tester.run_all_tests()
    
    # Print detailed summary
    summary = tester.get_summary()
    print(f"\n📋 Detailed Summary:")
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Passed: {summary['passed']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Success Rate: {summary['success_rate']}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())