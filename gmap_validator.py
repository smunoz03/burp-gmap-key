# Jython-compatible version using Java HTTP client
from java.net import URL, HttpURLConnection
from java.io import BufferedReader, InputStreamReader
import json
import time

class GoogleMapsValidator:
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.google_api_key = self.config.get('google_service_account_key')
        self.validation_cache = {}
        
        # Google Maps API endpoints for validation
        self.test_endpoints = {
            'maps_javascript': 'https://maps.googleapis.com/maps/api/js?key={key}',
            'static_maps': 'https://maps.googleapis.com/maps/api/staticmap?center=0,0&zoom=1&size=1x1&key={key}',
            'directions': 'https://maps.googleapis.com/maps/api/directions/json?origin=0,0&destination=1,1&key={key}',
            'places': 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=0,0&radius=1&key={key}',
            'geocoding': 'https://maps.googleapis.com/maps/api/geocode/json?address=test&key={key}',
            'distance_matrix': 'https://maps.googleapis.com/maps/api/distancematrix/json?origins=0,0&destinations=1,1&key={key}',
            'elevation': 'https://maps.googleapis.com/maps/api/elevation/json?locations=0,0&key={key}',
            'roads': 'https://roads.googleapis.com/v1/nearestRoads?points=0,0&key={key}',
            'streetview': 'https://maps.googleapis.com/maps/api/streetview/metadata?location=0,0&key={key}'
        }
        
        # Service display names and categories
        self.service_info = {
            'maps_javascript': {'name': 'Maps JavaScript API', 'category': 'maps'},
            'static_maps': {'name': 'Static Maps API', 'category': 'maps'},
            'directions': {'name': 'Directions API', 'category': 'routes'},
            'places': {'name': 'Places API', 'category': 'places'},
            'geocoding': {'name': 'Geocoding API', 'category': 'geocoding'},
            'distance_matrix': {'name': 'Distance Matrix API', 'category': 'routes'},
            'elevation': {'name': 'Elevation API', 'category': 'elevation'},
            'roads': {'name': 'Roads API', 'category': 'roads'},
            'streetview': {'name': 'Street View API', 'category': 'streetview'}
        }
    
    def _make_http_request(self, url_string, timeout=5000):
        """
        Make HTTP request using Java's HttpURLConnection with retry logic
        """
        max_retries = self.config.get('max_retries', 3)
        last_error = None

        for attempt in range(max_retries):
            try:
                url = URL(url_string)
                connection = url.openConnection()
                connection.setRequestMethod("GET")
                connection.setConnectTimeout(timeout)
                connection.setReadTimeout(timeout)
                connection.setRequestProperty("User-Agent", "Gmapper/1.0")

                response_code = connection.getResponseCode()

                # Read response
                response = ""
                if response_code == 200:
                    reader = BufferedReader(InputStreamReader(connection.getInputStream()))
                    line = reader.readLine()
                    while line is not None:
                        response += line
                        line = reader.readLine()
                    reader.close()

                    return {
                        'status_code': response_code,
                        'text': response,
                        'success': True
                    }
                else:
                    # Try to read error stream for more details
                    try:
                        error_stream = connection.getErrorStream()
                        if error_stream:
                            reader = BufferedReader(InputStreamReader(error_stream))
                            line = reader.readLine()
                            while line is not None:
                                response += line
                                line = reader.readLine()
                            reader.close()
                    except:
                        pass

                    # Non-2xx responses are not retried (API errors, not network errors)
                    return {
                        'status_code': response_code,
                        'text': response,
                        'success': False
                    }

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    time.sleep(2 ** attempt)
                    continue

        return {
            'status_code': 0,
            'text': '',
            'success': False,
            'error': last_error or 'Request failed after {} retries'.format(max_retries)
        }
    
    def validate_key(self, api_key):
        """
        Validate a Google Maps API key and return its configuration details
        """
        # Check cache with TTL
        if api_key in self.validation_cache:
            cached = self.validation_cache[api_key]
            cache_ttl = self.config.get('cache_ttl', 3600)
            if self.config.get('enable_caching', True) and (time.time() - cached['timestamp']) < cache_ttl:
                return cached['result']

        result = {
            'valid': False,
            'key': api_key,
            'services': [],
            'restriction_status': 'UNKNOWN',
            'restrictions': {},
            'metadata': {}
        }

        # Test if key is valid
        validity_result = self._test_key_validity(api_key)

        if validity_result['valid']:
            result['valid'] = True

            # Test which services are enabled
            result['services'] = self._test_enabled_services(api_key)

            # Try to get key metadata if we have a service account key
            if self.google_api_key:
                metadata = self._get_key_metadata(api_key)
                if metadata:
                    result['metadata'] = metadata
                    result['restriction_status'] = self._determine_restriction_status(metadata)
                    result['restrictions'] = metadata.get('restrictions', {})
            else:
                # Infer restriction status from API responses
                result['restriction_status'] = self._infer_restriction_status(api_key)
        else:
            result['error'] = validity_result.get('error', 'Invalid API key')

        # Cache the result with timestamp
        if self.config.get('enable_caching', True):
            self.validation_cache[api_key] = {
                'result': result,
                'timestamp': time.time()
            }

        return result
    
    def _test_key_validity(self, api_key):
        """
        Test if the API key is valid by making a simple request
        """
        try:
            # Use static maps API for validation as it's simple and reliable
            test_url = self.test_endpoints['static_maps'].format(key=api_key)
            response = self._make_http_request(test_url)
            
            if response['success'] and response['status_code'] == 200:
                return {'valid': True}
            else:
                error_msg = 'HTTP {}'.format(response['status_code'])
                # Try to parse error details from response
                if response.get('text'):
                    try:
                        error_data = json.loads(response['text'])
                        if 'error' in error_data:
                            error_details = error_data['error']
                            if 'message' in error_details:
                                error_msg = '{} - {}'.format(error_msg, error_details['message'])
                            if 'errors' in error_details and error_details['errors']:
                                reasons = [e.get('reason', '') for e in error_details['errors']]
                                if reasons:
                                    error_msg = '{} ({})'.format(error_msg, ', '.join(reasons))
                    except:
                        # If it's not JSON, include the raw text if it's short
                        if len(response['text']) < 200:
                            error_msg = '{} - {}'.format(error_msg, response['text'])
                
                return {'valid': False, 'error': error_msg}
        except Exception as e:
            return {'valid': False, 'error': 'Network error: {}'.format(str(e))}
    
    def _test_enabled_services(self, api_key):
        """
        Test which Google Maps services are enabled for this key
        """
        enabled_services = []
        
        for service_id, endpoint_template in self.test_endpoints.items():
            service_name = self.service_info[service_id]['name']
            test_url = endpoint_template.format(key=api_key)
            
            try:
                response = self._make_http_request(test_url, timeout=3000)
                
                if response['success'] and response['status_code'] == 200:
                    # Service is enabled
                    enabled_services.append({
                        'id': service_id,
                        'name': service_name,
                        'enabled': True,
                        'category': self.service_info[service_id]['category']
                    })
                else:
                    # Check specific error messages in response
                    error_msg = ''
                    if response.get('text'):
                        try:
                            error_data = json.loads(response['text'])
                            error_msg = error_data.get('error', {}).get('message', '')
                        except:
                            pass
                    
                    # Service is disabled or restricted
                    enabled_services.append({
                        'id': service_id,
                        'name': service_name,
                        'enabled': False,
                        'category': self.service_info[service_id]['category'],
                        'error': error_msg or 'Service not enabled'
                    })
                    
            except Exception as e:
                # Error testing service
                enabled_services.append({
                    'id': service_id,
                    'name': service_name,
                    'enabled': False,
                    'category': self.service_info[service_id]['category'],
                    'error': str(e)
                })
        
        return enabled_services
    
    def _get_key_metadata(self, api_key):
        """
        Get detailed metadata about the key using Google Cloud API
        (Requires service account authentication)
        """
        # This would require implementing Google Cloud API authentication in Jython
        # For now, return None as this is optional functionality
        return None
    
    def _determine_restriction_status(self, metadata):
        """
        Determine the restriction status based on key metadata
        """
        if not metadata:
            return 'UNKNOWN'
        
        restrictions = metadata.get('restrictions', {})
        
        if not restrictions:
            return 'UNRESTRICTED'
        
        restriction_types = []
        
        if 'browserKeyRestrictions' in restrictions:
            restriction_types.append('HTTP_REFERRER')
        
        if 'serverKeyRestrictions' in restrictions:
            restriction_types.append('IP_ADDRESS')
        
        if 'androidKeyRestrictions' in restrictions:
            restriction_types.append('ANDROID_APP')
        
        if 'iosKeyRestrictions' in restrictions:
            restriction_types.append('IOS_APP')
        
        if restriction_types:
            return 'RESTRICTED ({})'.format(', '.join(restriction_types))
        
        return 'UNKNOWN'
    
    def _infer_restriction_status(self, api_key):
        """
        Try to infer restriction status by testing the key from different contexts
        """
        # For Burp extension context, we can't easily test different referrers/IPs
        # So return a generic status
        return 'UNKNOWN (test manually for restrictions)'