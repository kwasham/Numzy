"""Standalone test script for the extraction service.

This script allows you to test the receipt extraction functionality
without running the full API. It includes examples for:
- Testing with local image files
- Testing with URLs
- Testing with custom prompts
- Comparing results
"""

import asyncio
import base64
import os
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import required modules
from app.services.extraction_service import ExtractionService
from app.models.schemas import ReceiptDetails
from app.utils.image_processing import preprocess_image


def load_test_image(filepath: str) -> bytes:
    """Load an image file from disk."""
    with open(filepath, 'rb') as f:
        return f.read()


def create_test_receipt_image() -> bytes:
    """Create a simple test receipt image using PIL."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not installed. Run: pip install pillow")
        return b""
    
    # Create a white image
    img = Image.new('RGB', (400, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fall back to built-in if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Draw receipt content
    y_position = 20
    
    # Header
    draw.text((100, y_position), "STARBUCKS COFFEE", font=font, fill='black')
    y_position += 40
    draw.text((120, y_position), "123 Main Street", font=small_font, fill='black')
    y_position += 25
    draw.text((110, y_position), "San Francisco, CA", font=small_font, fill='black')
    y_position += 40
    
    # Date
    draw.text((50, y_position), f"Date: {datetime.now().strftime('%m/%d/%Y')}", font=small_font, fill='black')
    y_position += 30
    
    # Items
    draw.line((50, y_position, 350, y_position), fill='black')
    y_position += 20
    
    items = [
        ("Caffe Latte", "5.25"),
        ("Croissant", "3.50"),
        ("Orange Juice", "4.00")
    ]
    
    for item, price in items:
        draw.text((50, y_position), item, font=small_font, fill='black')
        draw.text((300, y_position), f"${price}", font=small_font, fill='black')
        y_position += 25
    
    # Totals
    draw.line((50, y_position, 350, y_position), fill='black')
    y_position += 20
    
    draw.text((50, y_position), "Subtotal:", font=small_font, fill='black')
    draw.text((300, y_position), "$12.75", font=small_font, fill='black')
    y_position += 25
    
    draw.text((50, y_position), "Tax:", font=small_font, fill='black')
    draw.text((300, y_position), "$1.02", font=small_font, fill='black')
    y_position += 25
    
    draw.text((50, y_position), "TOTAL:", font=font, fill='black')
    draw.text((290, y_position), "$13.77", font=font, fill='black')
    y_position += 40
    
    # Payment method
    draw.text((50, y_position), "Paid with: Visa ***1234", font=small_font, fill='black')
    
    # Save to bytes
    import io
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


async def test_basic_extraction():
    """Test basic extraction with a sample receipt."""
    print("\n=== Testing Basic Extraction ===")
    
    service = ExtractionService()
    
    # Create or load test image
    if os.path.exists("test_receipt.png"):
        print("Loading test_receipt.png...")
        image_data = load_test_image("test_receipt.png")
    else:
        print("Creating synthetic test receipt...")
        image_data = create_test_receipt_image()
        # Save for future use
        with open("test_receipt.png", "wb") as f:
            f.write(image_data)
    
    # Extract receipt details
    result = await service.extract(
        file_data=image_data,
        filename="test_receipt.png"
    )
    
    print(f"\nExtracted Details:")
    print(f"Merchant: {result.merchant}")
    print(f"Date: {result.time}")
    print(f"Total: {result.total}")
    print(f"Subtotal: {result.subtotal}")
    print(f"Tax: {result.tax}")
    print(f"Items: {len(result.items) if result.items else 0}")
    if result.items:
        for item in result.items:
            print(f"  - {item.description}: {item.item_price}")
    
    # Location info
    if result.location:
        print(f"Location: {result.location.city}, {result.location.state}")
    
    return result


async def test_custom_prompt():
    """Test extraction with a custom prompt."""
    print("\n=== Testing Custom Prompt ===")
    
    service = ExtractionService()
    
    # Custom prompt that emphasizes accuracy
    custom_prompt = """You are a precise receipt parser. Extract data with these priorities:
    1. EXACT merchant name (no abbreviations)
    2. Full date in YYYY-MM-DD format
    3. All line items with exact prices
    4. Payment method details
    
    Be extremely careful with numbers. Return data as ReceiptDetails JSON."""
    
    image_data = load_test_image("test_receipt.png") if os.path.exists("test_receipt.png") else create_test_receipt_image()
    
    result = await service.extract(
        file_data=image_data,
        filename="test_receipt.png",
        prompt=custom_prompt
    )
    
    merchant = getattr(result, 'merchant', getattr(result, 'merchant_name', 'N/A'))
    print(f"Custom extraction completed: {merchant}")
    return result


async def test_error_handling():
    """Test error handling with invalid data."""
    print("\n=== Testing Error Handling ===")
    
    service = ExtractionService()
    
    # Test with empty data
    result = await service.extract(
        file_data=b"invalid image data",
        filename="bad.jpg"
    )
    
    print(f"Result with bad data: {result}")
    print(f"Is empty: {result == ReceiptDetails()}")


async def test_pdf_extraction():
    """Test PDF extraction if a test PDF exists."""
    print("\n=== Testing PDF Extraction ===")
    
    if not os.path.exists("test_receipt.pdf"):
        print("No test_receipt.pdf found. Skipping PDF test.")
        return
    
    service = ExtractionService()
    pdf_data = load_test_image("test_receipt.pdf")
    
    result = await service.extract(
        file_data=pdf_data,
        filename="test_receipt.pdf"
    )
    
    print(f"PDF extraction result: {result.merchant_name}")
    return result


async def test_model_comparison():
    """Compare results between different models."""
    print("\n=== Testing Model Comparison ===")
    
    if not os.path.exists("test_receipt.png"):
        print("Creating test receipt first...")
        create_test_receipt_image()
    
    image_data = load_test_image("test_receipt.png")
    service = ExtractionService()
    
    models = ["gpt-4o-mini", "gpt-4o"]
    results = {}
    
    for model in models:
        print(f"\nTesting with {model}...")
        try:
            result = await service.extract(
                file_data=image_data,
                filename="test_receipt.png",
                model=model
            )
            results[model] = result
            total = getattr(result, 'total', getattr(result, 'total_amount', 0))
            # Handle total display
            if isinstance(total, str) and '$' in str(total):
                print(f"Success: Total={total}")
            else:
                print(f"Success: Total=${total}")
        except Exception as e:
            print(f"Error with {model}: {e}")
            results[model] = None
    
    # Compare results
    print("\n=== Comparison ===")
    for model, result in results.items():
        if result:
            merchant = getattr(result, 'merchant', getattr(result, 'merchant_name', 'N/A'))
            total = getattr(result, 'total', getattr(result, 'total_amount', 0))
            # Handle total display
            if isinstance(total, str) and '$' in str(total):
                print(f"{model}: {merchant} - {total}")
            else:
                print(f"{model}: {merchant} - ${total}")


async def test_batch_extraction():
    """Test extracting multiple receipts."""
    print("\n=== Testing Batch Extraction ===")
    
    service = ExtractionService()
    
    # Create multiple test images
    test_files = []
    for i in range(3):
        filename = f"test_receipt_{i}.png"
        if os.path.exists(filename):
            test_files.append((load_test_image(filename), filename))
        else:
            # Create with slight variations
            img_data = create_test_receipt_image()
            test_files.append((img_data, filename))
    
    # Extract all
    results = []
    for file_data, filename in test_files:
        result = await service.extract(file_data, filename)
        results.append(result)
        merchant = getattr(result, 'merchant', getattr(result, 'merchant_name', 'N/A'))
        total = getattr(result, 'total', getattr(result, 'total_amount', 0))
        print(f"{filename}: {merchant} - ${total}")
    
    return results


async def save_test_results(results: dict):
    """Save test results to a JSON file for analysis."""
    output = {
        "test_run": datetime.now().isoformat(),
        "results": {}
    }
    
    for test_name, result in results.items():
        if isinstance(result, ReceiptDetails):
            output["results"][test_name] = result.model_dump()
        else:
            output["results"][test_name] = str(result)
    
    with open("test_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to test_results.json")


async def main():
    """Run all tests."""
    print("Receipt Extraction Service Test Suite")
    print("====================================")
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set!")
        print("Set it with: export OPENAI_API_KEY=your-key-here")
        return
    
    results = {}
    
    # Run tests
    try:
        results["basic"] = await test_basic_extraction()
    except Exception as e:
        print(f"Basic extraction failed: {e}")
        results["basic"] = str(e)
    
    try:
        results["custom_prompt"] = await test_custom_prompt()
    except Exception as e:
        print(f"Custom prompt test failed: {e}")
        results["custom_prompt"] = str(e)
    
    try:
        await test_error_handling()
    except Exception as e:
        print(f"Error handling test encountered: {e}")
    
    try:
        results["pdf"] = await test_pdf_extraction()
    except Exception as e:
        print(f"PDF test failed: {e}")
        results["pdf"] = str(e)
    
    # Optional: test model comparison (costs more)
    if input("\nRun model comparison test? (y/n): ").lower() == 'y':
        await test_model_comparison()
    
    # Save results
    await save_test_results(results)
    
    print("\n=== Test Suite Complete ===")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())