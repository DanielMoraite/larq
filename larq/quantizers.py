"""A Quantizer defines the way of transforming a full precision input to a
quantized output and the pseudo-gradient method used for the backwards pass."""

import tensorflow as tf
from larq import utils


def sign(x):
    """A sign function that will never be zero"""
    return tf.sign(tf.sign(x) + 0.1)


@tf.custom_gradient
def _binarize_with_identity_grad(x):
    def grad(dy):
        return dy

    return sign(x), grad


@tf.custom_gradient
def _binarize_with_weighted_grad(x):
    def grad(dy):
        return (1 - tf.abs(x)) * 2 * dy

    return sign(x), grad


@utils.register_keras_custom_object
def ste_sign(x):
    r"""
    Sign binarization function.
    \\[
    q(x) = \begin{cases}
      -1 & x < 0 \\\
      1 & x \geq 0
    \end{cases}
    \\]

    The gradient is estimated using the Straight-Through Estimator
    (essentially the binarization is replaced by a clipped identity on the
    backward pass).
    \\[\frac{\partial q(x)}{\partial x} = \begin{cases}
      1 & \left|x\right| \leq 1 \\\
      0 & \left|x\right| > 1
    \end{cases}\\]

    # Arguments
    x: Input tensor.

    # Returns
    Binarized tensor.

    # References
    - [Binarized Neural Networks: Training Deep Neural Networks with Weights and
      Activations Constrained to +1 or -1](http://arxiv.org/abs/1602.02830)
    """

    x = tf.clip_by_value(x, -1, 1)

    return _binarize_with_identity_grad(x)


@utils.register_keras_custom_object
def approx_sign(x):
    r"""
    Sign binarization function.
    \\[
    q(x) = \begin{cases}
      -1 & x < 0 \\\
      1 & x \geq 0
   \end{cases}
   \\]

    The gradient is estimated using the ApproxSign method.
    \\[\frac{\partial q(x)}{\partial x} = \begin{cases}
      (2 - 2 \left|x\right|) & \left|x\right| \leq 1 \\\
      0 & \left|x\right| > 1
    \end{cases}
    \\]

    # Arguments
    x: Input tensor.

    # Returns
    Binarized tensor.

    # References
    - [Bi-Real Net: Enhancing the Performance of 1-bit CNNs With Improved
      Representational Capability and Advanced
      Training Algorithm](http://arxiv.org/abs/1808.00278)
    """

    x = tf.clip_by_value(x, -1, 1)

    return _binarize_with_weighted_grad(x)


def tern(x):
    x_sum = tf.reduce_sum(tf.abs(x), reduction_indices=None, keep_dims=False, name=None)
    threshold = tf.div(x_sum, tf.cast(tf.size(x), tf.float32), name=None)
    threshold = tf.multiply(0.7, threshold, name=None)
    return tf.sign(
        tf.add(tf.sign(tf.add(x, threshold)), tf.sign(tf.add(x, -threshold)))
    )


@tf.custom_gradient
def _ternarize_with_identity_grad(x):
    def grad(dy):
        return dy

    return tern(x), grad


@utils.register_keras_custom_object
def ste_tern(x):
    r"""
    Ternarization function.
    \\[
    q(x) = \begin{cases}
      +1 & x > \Delta \\\
      0 & |x| > \Delta \\\
      -1 & x < \Delta
    \end{cases}
    \\]

    The Threshold is then calculated as
    \\[
    \Delta = \frac{0.7}{n} \sum_{i=1}^{n} |W_i|
    \\]
    where we assume that $W_i$ is generated from a normal distribution

    The gradient is estimated using the Straight-Through Estimator
    (essentially the Ternarization is replaced by a clipped identity on the
    backward pass).
    \\[\frac{\partial q(x)}{\partial x} = \begin{cases}
      1 & \left|x\right| \leq 1 \\\
      0 & \left|x\right| > 1
    \end{cases}\\]

    # Arguments
    x: Input tensor.

    # Returns
    Ternarized tensor.

    # References
    - [Ternary Weight Networks](http://arxiv.org/abs/1605.04711)
    """
    x = tf.clip_by_value(x, -1, 1)

    return _ternarize_with_identity_grad(x)


def serialize(initializer):
    return tf.keras.utils.serialize_keras_object(initializer)


def deserialize(name, custom_objects=None):
    return tf.keras.utils.deserialize_keras_object(
        name,
        module_objects=globals(),
        custom_objects=custom_objects,
        printable_module_name="quantization function",
    )


def get(identifier):
    if identifier is None:
        return None
    if isinstance(identifier, str):
        return deserialize(str(identifier))
    if callable(identifier):
        return identifier
    raise ValueError(
        f"Could not interpret quantization function identifier: {identifier}"
    )