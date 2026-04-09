"""
Utility to download Piper TTS voice models automatically.
Models are pulled from the Hugging Face rhasspy/piper-voices repository.
"""

import os
import requests
import logging

MODELS_DIR = os.path.join(os.path.dirname(__file__), "piper_models")

def get_piper_model(voice_name="en_GB-alan-medium"):
    """
    Downloads the ONNX model and JSON config for the specified Piper voice.
    Returns (onnx_path, json_path) if successful, else (None, None).
    """
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    onnx_path = os.path.join(MODELS_DIR, f"{voice_name}.onnx")
    json_path = os.path.join(MODELS_DIR, f"{voice_name}.onnx.json")

    if os.path.exists(onnx_path) and os.path.exists(json_path):
        return onnx_path, json_path

    # Extract language from voice name, e.g., "en_GB-alan-medium" -> "en_GB" -> "en"
    parts = voice_name.split('-')
    if len(parts) == 3:
        lang, name, quality = parts
        base_lang = lang.split('_')[0]
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{base_lang}/{lang}/{name}/{quality}"
    else:
        logging.error(f"Unsupported piper voice format: {voice_name}")
        return None, None

    def download_file(url, path):
        logging.info(f"Downloading Piper TTS Model from {url} ...")
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    try:
        download_file(f"{base_url}/{voice_name}.onnx", onnx_path)
        download_file(f"{base_url}/{voice_name}.onnx.json", json_path)
        logging.info(f"Downloaded fully local neural voice model: {voice_name}")
        return onnx_path, json_path
    except Exception as e:
        logging.error(f"Failed to download Piper model {voice_name}: {e}")
        # Clean up partial downloads
        if os.path.exists(onnx_path): os.remove(onnx_path)
        if os.path.exists(json_path): os.remove(json_path)
        return None, None
