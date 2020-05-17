import numpy as np
import torch

from .learning_rule import LearningRule


class KrotovsRule(LearningRule):
    """Krotov-Hopfield Hebbian learning rule fast implementation.

    Original source: https://github.com/DimaKrotov/Biological_Learning

    Args:
        precision: Numerical precision of the weight updates.
        delta: Anti-hebbian learning strength.
        norm: Lebesgue norm of the weights.
        k: Ranking parameter
    """

    def __init__(self, precision=1e-30, delta=0.4, norm=2, k=2):
        super().__init__()
        self.precision = precision
        self.delta = delta
        self.norm = norm
        self.k = k

    def init_layers(self, layers: list):
        for layer in [lyr.layer for lyr in layers]:
            if type(layer) == torch.nn.Linear or type(layer) == torch.nn.Conv2d:
                layer.weight.data.normal_(mean=0.0, std=1.0)

    def update(self, inputs: torch.Tensor, weights: torch.Tensor):
        batch_size = inputs.shape[0]
        num_hidden_units = weights.shape[0]
        input_size = inputs[0].shape[0]
        inputs = torch.t(inputs)
        assert (self.k <= num_hidden_units), "The amount of hidden units should be larger or equal to k!"

        # Calculate overlap with data for each hidden neuron and batch
        tot_input = torch.matmul(torch.sign(weights) * torch.abs(weights) ** (self.norm - 1), inputs)

        # Get the top k largest activations for each batch
        _, indices = torch.topk(tot_input, k=self.k, dim=0)

        # Activations of post-synaptic neurons for each batch
        activations = torch.zeros((num_hidden_units, batch_size))
        activations[indices[0], torch.arange(batch_size)] = 1.0
        activations[indices[self.k - 1], torch.arange(batch_size)] = -self.delta

        # Sum the activations in each batch, the batch dimension is removed here
        xx = torch.sum(torch.mul(activations, tot_input), 1)

        # Apply the actual learning rule, from here on the tensor has the same dimension as the weights
        norm_factor = torch.mul(xx.view(xx.shape[0], 1).repeat((1, input_size)), weights)
        ds = torch.matmul(activations, torch.t(inputs)) - norm_factor

        # Normalize the weight updates so that the largest update is 1 (which is then multiplied by the learning rate)
        nc = torch.max(torch.abs(ds))
        if nc < self.precision:
            nc = self.precision
        d_w = torch.true_divide(ds, nc)

        return d_w

    def update_argsort(self, inputs: torch.Tensor, weights: torch.Tensor):
        batch_size = inputs.shape[0]
        num_hidden_units = weights.shape[0]
        input_size = inputs[0].shape[0]
        inputs = torch.t(inputs)
        assert (self.k <= num_hidden_units), "The amount of hidden units should be larger or equal to k!"

        # Calculate overlap with data for each hidden neuron and batch
        tot_input = torch.matmul(torch.sign(weights) * torch.abs(weights) ** (self.norm - 1), inputs)

        # Sorting the activation strengths for each batch
        y = torch.argsort(tot_input, dim=0)

        # Activations of post-synaptic neurons for each batch
        activations = torch.zeros((num_hidden_units, batch_size))
        activations[y[num_hidden_units - 1, :], torch.arange(batch_size)] = 1.0
        activations[y[num_hidden_units - self.k], torch.arange(batch_size)] = -self.delta

        # Sum the activations in each batch, the batch dimension is removed here
        xx = torch.sum(torch.mul(activations, tot_input), 1)

        # Apply the actual learning rule, from here on the tensor has the same dimension as the weights
        norm_factor = torch.mul(xx.view(xx.shape[0], 1).repeat((1, input_size)), weights)
        ds = torch.matmul(activations, torch.t(inputs)) - norm_factor

        # Normalize the weight updates so that the largest update is 1 (which is then multiplied by the learning rate)
        nc = torch.max(torch.abs(ds))
        if nc < self.precision:
            nc = self.precision
        d_w = torch.true_divide(ds, nc)

        return d_w

    # TODO: TEMP
    def update_np(self, inputs, synapses):
        hid = synapses.shape[0]
        Num = inputs.shape[0]
        N = inputs[0].shape[0]
        delta = self.delta
        prec = self.precision
        k = self.k
        p = self.norm

        inputs = inputs.detach().cpu().numpy()
        synapses = synapses.detach().cpu().numpy()

        inputs = np.transpose(inputs)
        sig = np.sign(synapses)
        tot_input = np.dot(sig * np.absolute(synapses) ** (p - 1), inputs)

        y = np.argsort(tot_input, axis=0)
        yl = np.zeros((hid, Num))
        yl[y[hid - 1, :], np.arange(Num)] = 1.0
        yl[y[hid - k], np.arange(Num)] = -delta

        xx = np.sum(np.multiply(yl, tot_input), 1)
        ds = np.dot(yl, np.transpose(inputs)) - np.multiply(np.tile(xx.reshape(xx.shape[0], 1), (1, N)), synapses)

        nc = np.amax(np.absolute(ds))
        if nc < prec:
            nc = prec
        d_w = torch.from_numpy(np.true_divide(ds, nc))

        return d_w
