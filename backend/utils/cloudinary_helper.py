import cloudinary.uploader
import os

def upload_image_to_cloudinary(file, folder="shopbygold"):
    """
    Upload any file to Cloudinary and return the secure URL
    folder = shopbygold/products, shopbygold/sliders etc
    """
    try:
        # file can be Flask FileStorage
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image"
        )
        print(f"✅ Cloudinary Upload Success: {result['secure_url']}")
        return result['secure_url']
    except Exception as e:
        print(f"❌ Cloudinary Upload Failed: {e}")
        return None