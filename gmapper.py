from burp import IBurpExtender, IHttpListener, IScanIssue
from java.lang import RuntimeException
from java.net import URL
import re
import json
import base64
import os
from datetime import datetime
import traceback

class BurpExtender(IBurpExtender, IHttpListener):
    
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        
        callbacks.setExtensionName("Gmapper - Google Maps API Key Scanner")
        callbacks.registerHttpListener(self)
        
        self._stdout = callbacks.getStdout()
        self._stderr = callbacks.getStderr()
        
        self.print_output("Gmapper extension loaded successfully")
        self.print_output("Monitoring HTTP traffic for Google Maps API keys...")
        
        # Import additional modules
        try:
            from gmap_validator import GoogleMapsValidator
            from cost_calculator import CostCalculator
            from config_manager import ConfigManager

            self.config = ConfigManager()
            self.validator = GoogleMapsValidator(self.config)
            self.calculator = CostCalculator()
            self.processed_keys = set()

            # Print example config if no config file exists
            if not os.path.exists('gmapper_config.json'):
                self.print_output("No config file found. You can create gmapper_config.json with:")
                self.print_output(self.config.get_example_config())

        except ImportError as e:
            self.print_error("Failed to import required modules: {}".format(e))
            self.print_error("Please ensure all extension files are in the same directory")
    
    def print_output(self, message):
        self._stdout.write("[Gmapper] {}\n".format(message).encode())
    
    def print_error(self, message):
        self._stderr.write("[Gmapper ERROR] {}\n".format(message).encode())
    
    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        try:
            # Only process responses
            if messageIsRequest:
                return

            # Check if this tool should be monitored
            if not self.config.should_monitor_tool(toolFlag):
                return

            # Get request URL for context and check host exclusion
            request_info = self._helpers.analyzeRequest(messageInfo)
            url = request_info.getUrl()

            if self.config.is_host_excluded(url.getHost()):
                return

            # Get response data
            response = messageInfo.getResponse()
            if not response:
                return

            response_str = self._helpers.bytesToString(response)

            # Extract API keys
            api_keys = self.extract_api_keys(response_str)
            
            # Process each found key
            for key in api_keys:
                if key not in self.processed_keys:
                    self.processed_keys.add(key)
                    self.process_api_key(key, url, messageInfo)
                    
        except Exception as e:
            self.print_error("Error processing HTTP message: {}".format(e))
            self.print_error(traceback.format_exc())
    
    def extract_api_keys(self, content):
        # Google Maps API key pattern - matches AIza followed by 35 alphanumeric/dash/underscore chars
        # This single pattern reliably matches all Google API key formats
        pattern = r'AIza[0-9A-Za-z\-_]{35}'
        return set(re.findall(pattern, content))
    
    def process_api_key(self, api_key, url, messageInfo):
        self.print_output("Found API key: {}... at {}".format(api_key[:20], url))

        try:
            # Validate key and get metadata
            validation_result = self.validator.validate_key(api_key)

            if validation_result['valid']:
                # Calculate costs
                cost_analysis = self.calculator.calculate_costs(validation_result['services'])

                # Generate abuse scenarios
                abuse_scenarios = self.calculator.generate_abuse_scenarios(validation_result['services'])

                # Create summary table
                self.print_summary_table(api_key, validation_result, cost_analysis, abuse_scenarios)

                # Check if issue should be created
                if self.should_create_issue(validation_result, cost_analysis):
                    self.create_burp_issue(api_key, url, validation_result, cost_analysis, abuse_scenarios, messageInfo)
            else:
                self.print_output("Key validation failed: {}".format(validation_result.get('error', 'Unknown error')))

        except Exception as e:
            self.print_error("Error processing key {}...: {}".format(api_key[:20], e))
    
    def print_summary_table(self, api_key, validation_result, cost_analysis, abuse_scenarios=None):
        if not cost_analysis:
            self.print_output("No cost analysis available for key {}...".format(api_key[:20]))
            return

        self.print_output("\n" + "="*80)
        self.print_output("API Key: {}...".format(api_key[:20]))
        self.print_output("Restrictions: {}".format(validation_result['restriction_status']))
        self.print_output("-"*80)
        self.print_output("{:<30} {:<15} {:<15}".format('Service', 'Status', 'Cost per 1k'))
        self.print_output("-"*80)

        for service in cost_analysis[:-1]:  # Exclude total row from service list
            self.print_output("{:<30} {:<15} ${:<14.2f}".format(service['name'], service['status'], service['cost_per_1k']))

        total_cost = cost_analysis[-1].get('total_cost', 0)
        self.print_output("\nTotal potential cost per 1k requests: ${:.2f}".format(total_cost))

        # Print abuse scenarios if available
        if abuse_scenarios:
            self.print_output("\n" + "-"*80)
            self.print_output("POTENTIAL ABUSE SCENARIOS:")
            self.print_output("-"*80)
            for scenario in abuse_scenarios:
                self.print_output("{:<30} ${:,.2f}/month (${:,.2f}/year)".format(
                    scenario['name'],
                    scenario['total_monthly_cost'],
                    scenario['total_annual_cost']
                ))

        self.print_output("="*80 + "\n")
    
    def should_create_issue(self, validation_result, cost_analysis):
        # Check if unrestricted
        if validation_result['restriction_status'] == 'UNRESTRICTED':
            return True

        # Check if cost exceeds threshold
        if not cost_analysis:
            return False

        threshold = self.config.get('cost_threshold', 5.0)
        total_cost = cost_analysis[-1].get('total_cost', 0)

        return total_cost > threshold
    
    def create_burp_issue(self, api_key, url, validation_result, cost_analysis, abuse_scenarios, messageInfo):
        issue = GoogleMapsAPIKeyIssue(
            self._helpers,
            messageInfo,
            api_key,
            validation_result,
            cost_analysis,
            abuse_scenarios,
            self.config
        )
        self._callbacks.addScanIssue(issue)
        self.print_output("Created Burp issue for key: {}...".format(api_key[:20]))


class GoogleMapsAPIKeyIssue(IScanIssue):

    def __init__(self, helpers, messageInfo, api_key, validation_result, cost_analysis, abuse_scenarios, config):
        self._helpers = helpers
        self._messageInfo = messageInfo
        self._api_key = api_key
        self._validation = validation_result
        self._costs = cost_analysis
        self._abuse_scenarios = abuse_scenarios
        self._config = config
        self._request_info = helpers.analyzeRequest(messageInfo)
    
    def getUrl(self):
        return self._request_info.getUrl()
    
    def getIssueName(self):
        if self._validation['restriction_status'] == 'UNRESTRICTED':
            return "Unrestricted Google Maps API Key"
        else:
            return "Potentially Expensive Google Maps API Key"
    
    def getIssueType(self):
        return 0x08000000  # Extension generated issue type
    
    def getSeverity(self):
        if self._validation['restriction_status'] == 'UNRESTRICTED':
            return self._config.get('issue_severity_unrestricted', 'High')
        return self._config.get('issue_severity_expensive', 'Medium')
    
    def getConfidence(self):
        return "Certain"
    
    def getIssueBackground(self):
        return """
        <p>Google Maps API keys that lack proper restrictions can be abused by unauthorized 
        parties, leading to unexpected charges and quota exhaustion. Keys should be restricted 
        by HTTP referrer, IP address, or application restrictions based on their intended use.</p>
        
        <p>Common attack scenarios include:</p>
        <ul>
            <li>Unauthorized usage from different domains</li>
            <li>Automated scraping using exposed keys</li>
            <li>Denial of wallet attacks through quota exhaustion</li>
        </ul>
        """
    
    def getRemediationBackground(self):
        return """
        <p>To properly secure Google Maps API keys:</p>
        <ol>
            <li>Apply HTTP referrer restrictions for web applications</li>
            <li>Use IP restrictions for server-side applications</li>
            <li>Enable only required APIs for each key</li>
            <li>Monitor usage and set up billing alerts</li>
            <li>Rotate keys regularly</li>
        </ol>
        
        <p>References:</p>
        <ul>
            <li><a href="https://developers.google.com/maps/documentation/javascript/get-api-key#restrict_key">
                Google Maps API Key Best Practices</a></li>
            <li><a href="https://cloud.google.com/docs/authentication/api-keys#securing_an_api_key">
                Securing API Keys</a></li>
        </ul>
        """
    
    def getIssueDetail(self):
        total_cost = self._costs[-1].get('total_cost', 0) if self._costs else 0

        detail = """
        <p>A Google Maps API key was detected with the following characteristics:</p>

        <p><b>API Key (truncated):</b> {}...</p>
        <p><b>Restriction Status:</b> {}</p>
        <p><b>Estimated Cost per 1,000 requests:</b> ${:.2f}</p>

        <p><b>Enabled Services:</b></p>
        <table>
            <tr>
                <th>Service</th>
                <th>Status</th>
                <th>Cost per 1k requests</th>
            </tr>
        """.format(self._api_key[:20], self._validation['restriction_status'], total_cost)

        for service in self._costs[:-1]:  # Exclude total row
            detail += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>${:.2f}</td>
            </tr>
            """.format(service['name'], service['status'], service['cost_per_1k'])

        detail += "</table>"

        # Add abuse scenarios if available
        if self._abuse_scenarios:
            detail += """
            <p><b>Potential Abuse Scenarios:</b></p>
            <table>
                <tr>
                    <th>Scenario</th>
                    <th>Monthly Cost</th>
                    <th>Annual Cost</th>
                </tr>
            """
            for scenario in self._abuse_scenarios:
                detail += """
                <tr>
                    <td>{} ({})</td>
                    <td>${:,.2f}</td>
                    <td>${:,.2f}</td>
                </tr>
                """.format(scenario['name'], scenario['description'],
                          scenario['total_monthly_cost'], scenario['total_annual_cost'])
            detail += "</table>"

        detail += """
        <p>This key should be reviewed and properly restricted to prevent unauthorized usage.</p>
        """

        return detail
    
    def getHttpMessages(self):
        return [self._messageInfo]
    
    def getHttpService(self):
        return self._messageInfo.getHttpService()
    
    def getRemediationDetail(self):
        return None