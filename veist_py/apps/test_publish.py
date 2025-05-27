#!/usr/bin/env python3
"""
Test script for NFT publishing
Tests each step separately for debugging
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from apps.publish import AkaSwapPublisher
import json

# Test credentials from the docs
TEST_PARTNER_ID = "aka-gptqgzidcn"
TEST_PARTNER_SECRET = "d3b2e436a2dcb4571385aacf779d9858b9ad5a643e8dc10c9255c1a3a2014b12"
TEST_RECEIVER = "tz2J3uKDJ9s68RtX1XSsqQB6ENRS3wiL1HR5"  # Test wallet from docs

def test_ipfs_upload():
    """Test just the IPFS upload step"""
    print("=== Testing IPFS Upload ===")
    
    # Find a test image
    test_images = list(Path("outputs").glob("*.jpg")) + list(Path("outputs").glob("*.png"))
    if not test_images:
        print("No test images found in outputs/")
        return None
        
    test_image = str(test_images[0])
    print(f"Using test image: {test_image}")
    
    publisher = AkaSwapPublisher(TEST_PARTNER_ID, TEST_PARTNER_SECRET)
    
    try:
        result = publisher.upload_to_ipfs(test_image)
        print("\nIPFS Upload Result:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"IPFS Upload failed: {e}")
        return None

def test_full_publish():
    """Test the complete publish flow"""
    print("\n=== Testing Full Publish Flow ===")
    
    # Find a test image
    test_images = list(Path("outputs").glob("*.jpg")) + list(Path("outputs").glob("*.png"))
    if not test_images:
        print("No test images found in outputs/")
        return
        
    test_image = str(test_images[0])
    print(f"Using test image: {test_image}")
    
    publisher = AkaSwapPublisher(TEST_PARTNER_ID, TEST_PARTNER_SECRET)
    
    try:
        result = publisher.publish_image(
            image_path=test_image,
            name="Veist Test NFT",
            description="Test NFT from VeistGeneratorBot",
            receiver_address=TEST_RECEIVER
        )
        print("\nFull Publish Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Full publish failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    print("Testing akaSwap NFT Publishing\n")
    
    # Check for command line argument
    skip_mint = '--skip-mint' in sys.argv
    
    # Test IPFS upload first
    ipfs_result = test_ipfs_upload()
    
    if ipfs_result:
        print("\n✅ IPFS upload successful!")
        
        if not skip_mint:
            print("\nProceeding with full NFT minting test...")
            test_full_publish()
        else:
            print("\nSkipping mint test (--skip-mint flag used)")
    else:
        print("\n❌ IPFS upload failed, skipping mint test")