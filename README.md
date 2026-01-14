# Gmapper - Google Maps API Key Scanner for BurpSuite

A Python-based BurpSuite extension that automatically detects and validates Google Maps API keys in HTTP traffic, assesses their security posture, and estimates potential cost impact from abuse.

## Features

- **Automatic Detection**: Scans HTTP responses for Google Maps API key patterns (`AIza...`)
- **Key Validation**: Tests discovered keys against 9 Google Maps services
- **Security Assessment**: Identifies unrestricted or weakly restricted API keys
- **Cost Analysis**: Calculates potential abuse costs based on current Google pricing
- **Abuse Scenarios**: Estimates financial impact at low/medium/high volume abuse levels
- **Burp Integration**: Creates detailed security issues in BurpSuite for vulnerable keys
- **Configurable**: Customize thresholds, severity levels, monitored tools, and host exclusions
- **Resilient**: Retry logic with exponential backoff for network failures
- **Efficient**: Caching with configurable TTL to avoid redundant API calls

## Installation

1. Ensure you have Jython installed and configured in BurpSuite:
   - Download Jython standalone JAR from https://www.jython.org/download
   - In Burp, go to Extensions → Options → Python Environment
   - Select the Jython JAR file

2. Clone or download this repository

3. In BurpSuite:
   - Go to Extensions → Installed
   - Click "Add"
   - Extension type: Python
   - Select the `gmapper.py` file

4. The extension will start monitoring HTTP traffic automatically

**Note**: If no config file is found, the extension will print an example configuration to the output tab.

## Configuration

Copy the example config and customize as needed:

```bash
cp gmapper_config.example.json gmapper_config.json
```

Configuration file (`gmapper_config.json`):

```json
{
  "cost_threshold": 5.0,
  "google_service_account_key": null,
  "enable_caching": true,
  "cache_ttl": 3600,
  "request_timeout": 5,
  "max_retries": 3,
  "log_level": "INFO",
  "create_issues": true,
  "issue_severity_unrestricted": "High",
  "issue_severity_expensive": "Medium",
  "monitored_tools": ["proxy"],
  "excluded_hosts": ["localhost", "127.0.0.1"],
  "pricing_overrides": {},
  "report_format": "table"
}
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `cost_threshold` | 5.0 | Cost per 1k requests that triggers an issue (USD) |
| `google_service_account_key` | null | Path to Google Cloud service account JSON (optional) |
| `enable_caching` | true | Cache validation results to reduce API calls |
| `cache_ttl` | 3600 | Cache time-to-live in seconds |
| `request_timeout` | 5 | HTTP request timeout in seconds |
| `max_retries` | 3 | Number of retry attempts for failed network requests |
| `create_issues` | true | Whether to create Burp issues for findings |
| `issue_severity_unrestricted` | "High" | Severity for unrestricted keys |
| `issue_severity_expensive` | "Medium" | Severity for expensive but restricted keys |
| `monitored_tools` | ["proxy"] | Burp tools to monitor (proxy, scanner, intruder, repeater) |
| `excluded_hosts` | [] | Hosts to exclude from scanning |
| `pricing_overrides` | {} | Custom pricing per service (e.g., `{"maps_javascript": 8.00}`) |

## Usage

1. **Browse Target Application**: Use Burp's proxy to browse the target application
2. **Monitor Extension Output**: Check the Extensions tab output for detected keys
3. **Review Issues**: Check the Target → Issues tab for detailed findings

### Sample Output

```
[Gmapper] Found API key: AIzaSyD-9tSrke72PouQM... at https://example.com

================================================================================
API Key: AIzaSyD-9tSrke72PouQM...
Restrictions: UNRESTRICTED
--------------------------------------------------------------------------------
Service                        Status          Cost per 1k
--------------------------------------------------------------------------------
Maps JavaScript API            Enabled         $7.00
Static Maps API                Enabled         $2.00
Directions API                 Enabled         $5.00
Places API                     Enabled         $17.00
Geocoding API                  Enabled         $5.00

Total potential cost per 1k requests: $36.00

--------------------------------------------------------------------------------
POTENTIAL ABUSE SCENARIOS:
--------------------------------------------------------------------------------
Low Volume Abuse               $35,964.00/month ($431,568.00/year)
Medium Volume Abuse            $359,964.00/month ($4,319,568.00/year)
High Volume Abuse              $3,599,964.00/month ($43,199,568.00/year)
================================================================================
```

## Detected Services

The extension tests for the following Google Maps Platform services:

| Service | Endpoint | Cost per 1k |
|---------|----------|-------------|
| Maps JavaScript API | maps.googleapis.com/maps/api/js | $7.00 |
| Static Maps API | maps.googleapis.com/maps/api/staticmap | $2.00 |
| Directions API | maps.googleapis.com/maps/api/directions | $5.00 |
| Places API | maps.googleapis.com/maps/api/place | $17.00 |
| Geocoding API | maps.googleapis.com/maps/api/geocode | $5.00 |
| Distance Matrix API | maps.googleapis.com/maps/api/distancematrix | $5.00 |
| Elevation API | maps.googleapis.com/maps/api/elevation | $5.00 |
| Roads API | roads.googleapis.com/v1/nearestRoads | $10.00 |
| Street View Static API | maps.googleapis.com/maps/api/streetview | $7.00 |

## Security Findings

The extension classifies keys based on restriction status:

| Status | Severity | Description |
|--------|----------|-------------|
| UNRESTRICTED | High | No API key restrictions applied |
| RESTRICTED | Low | Proper IP/HTTP referrer/app restrictions |
| UNKNOWN | Medium | Cannot determine restriction status |

## Abuse Scenarios

The extension calculates potential financial impact at three volume levels:

- **Low Volume**: 1 million requests/month
- **Medium Volume**: 10 million requests/month
- **High Volume**: 100 million requests/month

These estimates help demonstrate the business impact of exposed API keys.

## Architecture

```
gmapper.py          - Main Burp extension and issue reporting
gmap_validator.py   - API key validation and service testing
cost_calculator.py  - Pricing calculations and abuse scenarios
config_manager.py   - Configuration management
```

## Limitations

- Requires active HTTP traffic through Burp proxy
- Cannot test IP restrictions from client perspective
- Google API metadata requires service account credentials
- Rate limiting may affect bulk key validation
- Keys must appear in HTTP response bodies to be detected

## Contributing

Pull requests are welcome! Please ensure:
- Code follows Python best practices
- New features include appropriate error handling
- Documentation is updated for new functionality
- Code is compatible with Jython 2.7

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for authorized security testing only. Users are responsible for complying with all applicable laws and regulations. Do not use this tool to test systems you don't have permission to test.

## Support

For issues, feature requests, or questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Ensure you're using the latest version

## Acknowledgments

- Google Maps Platform documentation
- BurpSuite Extensibility API
- Jython project for Python integration
