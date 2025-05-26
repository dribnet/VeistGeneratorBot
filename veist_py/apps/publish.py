#!/usr/bin/env python3
"""
NFT Publishing utility for VeistGeneratorBot
Publishes images to akaSwap on Tezos blockchain
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import requests
from PIL import Image
import io

# API Configuration
API_BASE_URL = "https://testnets.akaswap.com/api/v2"
DEFAULT_CONTRACT = "KT1BgHYwDH1GyHUcyfz8Ykfzuz7KvpRuAz1v"  # From docs

class AkaSwapPublisher:
    def __init__(self, partner_id: str, partner_secret: str):
        self.partner_id = partner_id
        self.partner_secret = partner_secret
        self.auth_header = self._create_auth_header()
        
    def _create_auth_header(self) -> str:
        """Create Basic Auth header from partner credentials"""
        credentials = f"{self.partner_id}:{self.partner_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _resize_image(self, image_path: str, max_size: Tuple[int, int]) -> bytes:
        """Resize image for different display levels"""
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
                
            # Resize while maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95)
            return output.getvalue()
    
    def upload_to_ipfs(self, image_path: str) -> Dict[str, str]:
        """Upload image to IPFS with three quality levels"""
        print(f"Uploading {image_path} to IPFS...")
        
        # Prepare three versions of the image
        artifact_data = self._resize_image(image_path, (2048, 2048))  # High quality
        display_data = self._resize_image(image_path, (1024, 1024))   # Medium quality
        thumbnail_data = self._resize_image(image_path, (256, 256))   # Thumbnail
        
        # Prepare multipart data
        files = {
            'artifacts': ('artifact.jpg', artifact_data, 'image/jpeg'),
            'display': ('display.jpg', display_data, 'image/jpeg'),
            'thumbnail': ('thumbnail.jpg', thumbnail_data, 'image/jpeg')
        }
        
        headers = {
            'Authorization': self.auth_header
        }
        
        response = requests.post(
            f"{API_BASE_URL}/ipfs/tokens",
            headers=headers,
            files=files
        )
        
        if response.status_code != 200:
            raise Exception(f"IPFS upload failed: {response.status_code} - {response.text}")
        
        result = response.json()
        print(f"Upload successful! IPFS URIs generated.")
        print(f"IPFS Response: {json.dumps(result, indent=2)}")
        return result
    
    def mint_nft(self, 
                 ipfs_data: Dict[str, str],
                 name: str,
                 description: str,
                 receiver_address: str,
                 amount: int = 1,
                 royalties: int = 100,  # 10% (in per-mille)
                 contract: str = DEFAULT_CONTRACT) -> Dict[str, Any]:
        """Mint an NFT on akaSwap"""
        print(f"Minting NFT: {name}")
        
        # Extract token ID from response
        token_id = ipfs_data.get('tokenId')
        if not token_id:
            # Generate token ID - must fit in Int32 range
            import time
            # Use modulo to keep it within Int32 range (max 2147483647)
            token_id = str(int(time.time() * 1000) % 2147483647)
        
        # Extract URIs from the actual response structure
        artifact_uri = ipfs_data.get('artifact', {}).get('uri')
        artifact_mime = ipfs_data.get('artifact', {}).get('mimeType')
        display_uri = ipfs_data.get('display', {}).get('uri')
        display_mime = ipfs_data.get('display', {}).get('mimeType')
        thumbnail_uri = ipfs_data.get('thumbnail', {}).get('uri')
        thumbnail_mime = ipfs_data.get('thumbnail', {}).get('mimeType')
        
        if not all([artifact_uri, display_uri, thumbnail_uri]):
            raise ValueError(f"Missing required URIs. Response: {ipfs_data}")
        
        # Based on error, API wants these fields at root level
        mint_data = {
            "tokenId": token_id,
            "address": receiver_address,  # Required field
            "amount": amount,
            "name": name,
            "description": description,
            "tags": ["veist", "ai-generated", "community"],  # Required field
            "symbol": "VEIST",  # Required field
            "isMint": True,
            "mint": {
                "address": receiver_address,
                "amount": amount
            },
            "transferable": True,
            "artifact": {
                "uri": artifact_uri,
                "mimeType": artifact_mime or 'image/jpeg'
            },
            "display": {
                "uri": display_uri,
                "mimeType": display_mime or 'image/jpeg'
            },
            "thumbnail": {
                "uri": thumbnail_uri,
                "mimeType": thumbnail_mime or 'image/jpeg'
            },
            "creators": [
                receiver_address  # Array of creator addresses
            ],
            "royalties": {
                "decimals": 2,
                "shares": {
                    receiver_address: 10  # 10% royalty
                }
            },
            "attributes": [
                {
                    "name": "generator",
                    "value": "VeistGeneratorBot"
                },
                {
                    "name": "consensus",
                    "value": "community_approved"
                }
            ]
        }
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json'
        }
        
        print(f"Mint request URL: {API_BASE_URL}/fa2tokens/{contract}")
        print(f"Mint request data: {json.dumps(mint_data, indent=2)}")
        
        response = requests.post(
            f"{API_BASE_URL}/fa2tokens/{contract}",
            headers=headers,
            json=mint_data
        )
        
        if response.status_code not in (200, 201):
            raise Exception(f"Minting failed: {response.status_code} - {response.text}")
        
        result = response.json()
        print(f"NFT minted successfully!")
        print(f"Token ID: {token_id}")
        print(f"Transaction: {result}")
        return result
    
    def publish_image(self, 
                     image_path: str,
                     name: str,
                     description: str,
                     receiver_address: str) -> Dict[str, Any]:
        """Complete publish flow: upload to IPFS and mint NFT"""
        # Step 1: Upload to IPFS
        ipfs_data = self.upload_to_ipfs(image_path)
        
        # Step 2: Mint NFT
        mint_result = self.mint_nft(
            ipfs_data=ipfs_data,
            name=name,
            description=description,
            receiver_address=receiver_address
        )
        
        return {
            "ipfs": ipfs_data,
            "mint": mint_result,
            "success": True
        }

def main():
    parser = argparse.ArgumentParser(description='Publish image as NFT on akaSwap')
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--name', required=True, help='NFT name')
    parser.add_argument('--description', required=True, help='NFT description')
    parser.add_argument('--receiver', required=True, help='Tezos wallet address to receive NFT')
    parser.add_argument('--partner-id', help='Partner ID (or set AKASWAP_PARTNER_ID env var)')
    parser.add_argument('--partner-secret', help='Partner secret (or set AKASWAP_PARTNER_SECRET env var)')
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    partner_id = args.partner_id or os.getenv('AKASWAP_PARTNER_ID')
    partner_secret = args.partner_secret or os.getenv('AKASWAP_PARTNER_SECRET')
    
    if not partner_id or not partner_secret:
        print("Error: Partner credentials required. Set via --partner-id/--partner-secret or environment variables")
        sys.exit(1)
    
    # Verify image exists
    if not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    try:
        publisher = AkaSwapPublisher(partner_id, partner_secret)
        result = publisher.publish_image(
            image_path=args.image,
            name=args.name,
            description=args.description,
            receiver_address=args.receiver
        )
        
        print("\n✅ Publishing complete!")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Publishing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()