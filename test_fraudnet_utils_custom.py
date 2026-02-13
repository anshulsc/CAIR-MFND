
import torch
import sys
import os

# Add the parent directory to sys.path to resolve src imports
sys.path.append('/data/asca/FND_mini')

try:
    from src import fraudnet_utils
    print("Successfully imported fraudnet_utils")
except ImportError as e:
    print(f"Failed to import fraudnet_utils: {e}")
    sys.exit(1)

def test_device_switching():
    print(f"Initial clip_device: {fraudnet_utils.clip_device}")
    
    # Ensure model is loaded
    fraudnet_utils.load_lavis_model()

    # Check if model is on CPU initially
    model_device = next(fraudnet_utils._LAVIS_MODEL.parameters()).device
    print(f"Model is initially on: {model_device}")
    
    if str(model_device) != 'cpu':
        print("Error: Model should be on CPU initially")
    
    # Test text feature extraction on CPU
    print("Testing text feature extraction on CPU...")
    try:
        feat_cpu = fraudnet_utils.get_clip_text_feature("test caption", device='cpu')
        print(f"Feature extracted on CPU. Shape: {feat_cpu.shape}, Device: {feat_cpu.device}")
    except Exception as e:
        print(f"Error on CPU extraction: {e}")

    # Test text feature extraction on CUDA if available
    if torch.cuda.is_available():
        print("Testing text feature extraction on CUDA...")
        try:
            feat_cuda = fraudnet_utils.get_clip_text_feature("test caption", device='cuda')
            print(f"Feature extracted on CUDA. Shape: {feat_cuda.shape}, Device: {feat_cuda.device}")
            
            # Check if model moved to CUDA
            model_device_after = next(fraudnet_utils._LAVIS_MODEL.parameters()).device
            print(f"Model is now on: {model_device_after}")
            
            if 'cuda' not in str(model_device_after):
                 print("Warning: Model should be on CUDA after usage")

        except Exception as e:
            print(f"Error on CUDA extraction: {e}")
    else:
        print("CUDA not available, skipping CUDA test")

if __name__ == "__main__":
    test_device_switching()
