# from typing import List, Dict  # Not supported in Jython
from datetime import datetime

class CostCalculator:
    
    def __init__(self):
        # Google Maps Platform pricing as of 2024
        # Prices are in USD per 1,000 requests
        self.pricing = {
            'maps_javascript': {
                'name': 'Maps JavaScript API',
                'static_map_loads': 7.00,  # Dynamic Maps
                'street_view': 14.00,
                'aerial_view': 14.00
            },
            'static_maps': {
                'name': 'Static Maps API',
                'default': 2.00,  # Up to 100,000 requests
                'premium': 1.60   # 100,001+ requests
            },
            'directions': {
                'name': 'Directions API',
                'basic': 5.00,              # Without traffic
                'advanced': 10.00,          # With traffic
                'advanced_next_departure': 20.00  # With next departure time
            },
            'places': {
                'name': 'Places API',
                'basic': 17.00,        # Basic Data
                'contact': 20.00,      # Contact Data
                'atmosphere': 25.00,   # Atmosphere Data
                'details': 17.00,      # Place Details
                'photos': 7.00,        # Place Photos
                'autocomplete': 2.83,  # Autocomplete (per session)
                'query_autocomplete': 5.66  # Query Autocomplete (per session)
            },
            'geocoding': {
                'name': 'Geocoding API',
                'default': 5.00  # Both geocoding and reverse geocoding
            },
            'distance_matrix': {
                'name': 'Distance Matrix API',
                'basic': 5.00,      # Per element (origin-destination pair)
                'advanced': 10.00   # With traffic
            },
            'elevation': {
                'name': 'Elevation API',
                'positional': 5.00,  # Positional requests
                'sampled_path': 10.00  # Sampled path requests
            },
            'roads': {
                'name': 'Roads API',
                'snap_to_roads': 10.00,    # Per 100 points
                'nearest_roads': 10.00,     # Per point
                'speed_limits': 20.00       # Per 100 points
            },
            'streetview': {
                'name': 'Street View Static API',
                'default': 7.00  # Per panorama
            }
        }
        
        # Free tier monthly quotas
        self.free_tier = {
            'maps_javascript': 28000,  # $200 credit covers ~28k loads
            'static_maps': 100000,
            'directions': 40000,
            'places': 11764,  # For basic requests
            'geocoding': 40000,
            'distance_matrix': 40000,
            'elevation': 40000,
            'roads': 20000,
            'streetview': 28571
        }
    
    def calculate_costs(self, enabled_services):
        """
        Calculate the potential costs for enabled services
        Returns a list with cost analysis for each service plus a total
        """
        cost_analysis = []
        total_cost = 0
        
        for service in enabled_services:
            service_id = service['id']
            service_name = service['name']
            
            if not service['enabled']:
                cost_analysis.append({
                    'id': service_id,
                    'name': service_name,
                    'status': 'Disabled',
                    'cost_per_1k': 0,
                    'monthly_free_tier': 0,
                    'details': 'Service not enabled for this key'
                })
                continue
            
            # Get pricing info
            if service_id in self.pricing:
                pricing_info = self.pricing[service_id]
                
                # Calculate average cost (using most common/basic tier)
                if service_id == 'maps_javascript':
                    cost = pricing_info['static_map_loads']
                    details = "Dynamic map loads: ${}/1k requests".format(cost)
                elif service_id == 'static_maps':
                    cost = pricing_info['default']
                    details = "Standard pricing: ${}/1k requests".format(cost)
                elif service_id == 'directions':
                    cost = pricing_info['basic']
                    details = "Basic directions (no traffic): ${}/1k requests".format(cost)
                elif service_id == 'places':
                    cost = pricing_info['details']  # Most common use case
                    details = "Place details: ${}/1k requests".format(cost)
                elif service_id == 'geocoding':
                    cost = pricing_info['default']
                    details = "Geocoding/Reverse geocoding: ${}/1k requests".format(cost)
                elif service_id == 'distance_matrix':
                    cost = pricing_info['basic']
                    details = "Basic distance matrix: ${}/1k elements".format(cost)
                elif service_id == 'elevation':
                    cost = pricing_info['positional']
                    details = "Positional requests: ${}/1k requests".format(cost)
                elif service_id == 'roads':
                    cost = pricing_info['nearest_roads']
                    details = "Nearest roads: ${}/1k points".format(cost)
                elif service_id == 'streetview':
                    cost = pricing_info['default']
                    details = "Street View panoramas: ${}/1k requests".format(cost)
                else:
                    cost = 5.00  # Default estimate
                    details = "Estimated cost"
                
                cost_analysis.append({
                    'id': service_id,
                    'name': service_name,
                    'status': 'Enabled',
                    'cost_per_1k': cost,
                    'monthly_free_tier': self.free_tier.get(service_id, 0),
                    'details': details
                })
                
                total_cost += cost
            else:
                # Unknown service
                cost_analysis.append({
                    'id': service_id,
                    'name': service_name,
                    'status': 'Enabled',
                    'cost_per_1k': 5.00,  # Conservative estimate
                    'monthly_free_tier': 0,
                    'details': 'Estimated cost (unknown service)'
                })
                total_cost += 5.00
        
        # Add total row
        cost_analysis.append({
            'id': 'total',
            'name': 'TOTAL POTENTIAL COST',
            'status': '',
            'cost_per_1k': total_cost,
            'total_cost': total_cost,
            'details': 'Combined cost if all services are used'
        })
        
        return cost_analysis
    
    def estimate_monthly_cost(self, service_id, requests_per_month):
        """
        Estimate monthly cost for a specific service based on request volume
        """
        if service_id not in self.pricing:
            return {
                'error': 'Unknown service: {}'.format(service_id),
                'cost': 0
            }
        
        free_requests = self.free_tier.get(service_id, 0)
        billable_requests = max(0, requests_per_month - free_requests)
        
        # Get base cost per 1k
        pricing_info = self.pricing[service_id]
        if service_id == 'maps_javascript':
            cost_per_1k = pricing_info['static_map_loads']
        elif service_id == 'static_maps':
            cost_per_1k = pricing_info['default']
        elif service_id == 'directions':
            cost_per_1k = pricing_info['basic']
        elif service_id == 'places':
            cost_per_1k = pricing_info['details']
        else:
            cost_per_1k = list(pricing_info.values())[1]  # First numeric value
        
        monthly_cost = (billable_requests / 1000) * cost_per_1k
        
        return {
            'service': service_id,
            'requests': requests_per_month,
            'free_tier': free_requests,
            'billable_requests': billable_requests,
            'cost_per_1k': cost_per_1k,
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12
        }
    
    def generate_abuse_scenarios(self, enabled_services):
        """
        Generate potential abuse scenarios and their costs
        """
        scenarios = []
        
        # Scenario 1: Low volume abuse (1M requests/month)
        low_volume = {
            'name': 'Low Volume Abuse',
            'description': '1 million requests per month',
            'monthly_requests': 1000000,
            'services': []
        }
        
        # Scenario 2: Medium volume abuse (10M requests/month)
        medium_volume = {
            'name': 'Medium Volume Abuse',
            'description': '10 million requests per month',
            'monthly_requests': 10000000,
            'services': []
        }
        
        # Scenario 3: High volume abuse (100M requests/month)
        high_volume = {
            'name': 'High Volume Abuse',
            'description': '100 million requests per month',
            'monthly_requests': 100000000,
            'services': []
        }
        
        for scenario in [low_volume, medium_volume, high_volume]:
            total_monthly_cost = 0
            
            for service in enabled_services:
                if service['enabled']:
                    cost_estimate = self.estimate_monthly_cost(
                        service['id'], 
                        scenario['monthly_requests']
                    )
                    scenario['services'].append({
                        'name': service['name'],
                        'monthly_cost': cost_estimate['monthly_cost']
                    })
                    total_monthly_cost += cost_estimate['monthly_cost']
            
            scenario['total_monthly_cost'] = total_monthly_cost
            scenario['total_annual_cost'] = total_monthly_cost * 12
            scenarios.append(scenario)
        
        return scenarios