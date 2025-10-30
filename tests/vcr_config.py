"""
VCR.py configuration for recording/replaying HTTP interactions.

This allows tests to run fast by replaying recorded API responses instead of
making real HTTP calls every time.
"""

import vcr

# Configure VCR instance
my_vcr = vcr.VCR(
    # Store cassettes in tests/cassettes/ directory
    cassette_library_dir='tests/cassettes',

    # Record mode: once = record once, then replay
    # Use 'new_episodes' to record new interactions but replay existing ones
    record_mode='once',

    # Match requests by method and URI
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query'],

    # Filter out sensitive data from recordings
    filter_headers=['authorization', 'x-api-key'],

    # Decode compressed responses for better diffs
    decode_compressed_response=True,

    # Serialize as YAML for human-readable diffs
    serializer='yaml',

    # Path transformer to organize cassettes
    path_transformer=vcr.VCR.ensure_suffix('.yaml'),
)


def scrub_request(request):
    """Remove sensitive data from recorded requests."""
    # Add any request scrubbing logic here
    return request


def scrub_response(response):
    """Remove sensitive data from recorded responses."""
    # Add any response scrubbing logic here
    return response


# Register request/response scrubbers
my_vcr.before_record_request = scrub_request
my_vcr.before_record_response = scrub_response
