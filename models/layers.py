import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional

@dataclass
class LayerState:
    """Container for layer's intermediate state during forward pass"""
    output: torch.Tensor
    pre_pool: Optional[torch.Tensor] = None
    pool_indices: Optional[torch.Tensor] = None

class ConvLayer(nn.Module):
    """A single convolutional layer with pooling and normalization"""
    def __init__(self, in_channels, out_channels, kernel_size, stride=1):
        super().__init__()
        # Calculate padding to maintain spatial dimensions
        padding = ((stride - 1) + kernel_size - 1) // 2
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride=stride, padding=padding)
        self.bn = nn.BatchNorm2d(out_channels)
        self.pool = nn.MaxPool2d(2, return_indices=True)
        
    def forward(self, x):
        """Forward pass through the layer
        
        Args:
            x: Input tensor
            
        Returns:
            LayerState containing output and intermediate states
        """
        # Convolution and activation
        x = self.conv(x)
        x = self.bn(x)
        x = F.relu(x)
        
        # Store pre-pool features
        pre_pool = x
        
        # Pooling
        x, indices = self.pool(x)
        
        return LayerState(output=x, pre_pool=pre_pool, pool_indices=indices)

class DeconvLayer(nn.Module):
    """A single deconvolutional layer with unpooling"""
    def __init__(self, conv_layer):
        super().__init__()
        self.conv_layer = conv_layer
        self.unpool = nn.MaxUnpool2d(kernel_size=2, stride=2)

    def forward(self, x, max_indices, pre_pool_size):
        """
        Args:
            x: Input tensor from the layer below
            max_indices: Indices from the max pooling operation in forward pass
            pre_pool_size: Size of the tensor before max pooling in forward pass
        """
        # Unpool to match the exact size from forward pass
        x = self.unpool(x, max_indices, output_size=pre_pool_size)
        
        # Flip kernel dimensions for transposed convolution
        weight = self.conv_layer.conv.weight.flip([2, 3])
        
        # Use same stride and padding as original conv
        stride = self.conv_layer.conv.stride
        padding = self.conv_layer.conv.padding
        output_padding = 1 if stride[0] > 1 else 0

        x = F.conv_transpose2d(x, weight, stride=stride, padding=padding, output_padding=output_padding)
        return x 