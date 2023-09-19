"""Deep Q-network architecture. Currently only LSTM is implemented."""

import numpy as np
import torch
from torch import nn

from explicit_memory.utils import split_by_possessive


class LSTM(nn.Module):
    """A simple LSTM network."""

    def __init__(
        self,
        capacity: dict,
        entities: list,
        relations: list,
        n_actions: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        embedding_dim: int = 32,
        batch_first: bool = True,
        device: str = "cpu",
        v1_params: dict = {
            "include_human": "sum",
            "human_embedding_on_object_location": False,
        },
        v2_params: dict = None,
        **kwargs,
    ) -> None:
        """Initialize the LSTM.

        Args
        ----
        capacity: the capacities of memory systems.
            e.g., {"episodic": 16, "semantic": 16, "short": 1}
        entities: list of entities, e.g., ["Foo", "Bar", "laptop", "phone", "desk",
            "lap"]
        relations : list of relations, e.g., ["atlocation", "north", "south"]
        n_actions: number of actions. This should be 3, at the moment.
        hidden_size: hidden size of the LSTM
        num_layers: number of the LSTM layers
        embedding_dim: entity embedding dimension (e.g., 32)
        batch_first: Should the batch dimension be the first or not.
        device: "cpu" or "cuda"
        v1_params: parameters for the v1 model.
            include_human:
                None: Don't include humans
                "sum": sum up the human embeddings with object / object_location embeddings.
                "cocnat": concatenate the human embeddings to object / object_location
                    embeddings.
            human_embedding_on_object_location: whether to superposition the human embedding
                on the tail (object location entity).

        """
        super().__init__()
        self.capacity = capacity
        self.memory_of_interest = list(self.capacity.keys())
        self.entities = entities
        self.relations = relations
        self.n_actions = n_actions
        self.embedding_dim = embedding_dim
        self.device = device
        self.v1_params = v1_params
        self.v2_params = v2_params

        if self.v1_params is None:
            assert self.v2_params is not None
            self.version = "v2"
            self.make_embedding = self.make_embedding_v2

        if self.v2_params is None:
            assert self.v1_params is not None
            self.version = "v1"
            self.make_embedding = self.make_embedding_v1

        self.create_embeddings()
        if "episodic" in self.memory_of_interest:
            self.lstm_e = nn.LSTM(
                self.input_size_e,
                hidden_size,
                num_layers,
                batch_first=batch_first,
                device=self.device,
            )
            self.fc_e0 = nn.Linear(hidden_size, hidden_size, device=self.device)
            self.fc_e1 = nn.Linear(hidden_size, hidden_size, device=self.device)

        if "semantic" in self.memory_of_interest:
            self.lstm_s = nn.LSTM(
                self.input_size_s,
                hidden_size,
                num_layers,
                batch_first=batch_first,
                device=self.device,
            )
            self.fc_s0 = nn.Linear(hidden_size, hidden_size, device=self.device)
            self.fc_s1 = nn.Linear(hidden_size, hidden_size, device=self.device)

        if "short" in self.memory_of_interest:
            self.lstm_o = nn.LSTM(
                self.input_size_o,
                hidden_size,
                num_layers,
                batch_first=batch_first,
                device=self.device,
            )
            self.fc_o0 = nn.Linear(hidden_size, hidden_size, device=self.device)
            self.fc_o1 = nn.Linear(hidden_size, hidden_size, device=self.device)

        self.fc_final0 = nn.Linear(
            hidden_size * len(self.memory_of_interest),
            hidden_size * len(self.memory_of_interest),
        )
        self.fc_final1 = nn.Linear(
            hidden_size * len(self.memory_of_interest), n_actions
        )
        self.relu = nn.ReLU()

    def create_embeddings(self) -> None:
        """Create learnable embeddings."""
        self.word2idx = ["<PAD>"] + self.entities + self.relations
        self.word2idx = {word: idx for idx, word in enumerate(self.word2idx)}
        self.embeddings = nn.Embedding(
            len(self.word2idx), self.embedding_dim, device=self.device, padding_idx=0
        )
        if self.version == "v1":
            self.input_size_s = self.embedding_dim * 2
            if (self.v1_params["include_human"] is None) or (
                self.v1_params["include_human"] == "sum"
            ):
                self.input_size_e = self.embedding_dim * 2
                self.input_size_o = self.embedding_dim * 2

            elif self.v1_params["include_human"] == "concat":
                self.input_size_e = self.embedding_dim * 3
                self.input_size_o = self.embedding_dim * 3
            else:
                raise ValueError(
                    "include_human should be one of None, 'sum', or 'concat', "
                    f"but {self.v1_params['include_human']} was given!"
                )
        elif self.version == "v2":  # [head, relation, tail]
            self.input_size_s = self.embedding_dim * 3
            self.input_size_e = self.embedding_dim * 3
            self.input_size_o = self.embedding_dim * 3

        else:
            raise ValueError(f"{self.version} is a wrong version!")

    def make_embedding_v1(self, mem: list, memory_type: str) -> torch.Tensor:
        """Create one embedding vector with summation and concatenation.

        Embeddings for v1

        Args
        ----
        mem: memory as a quadruple: [head, relation, tail, num]
        memory_type: "episodic", "semantic", or "short"

        Returns
        -------
        one embedding vector made from one memory element.

        """
        if mem == ["<PAD>", "<PAD>", "<PAD>", "<PAD>"]:
            human, obj, obj_loc = "<PAD>", "<PAD>", "<PAD>"
        else:
            if memory_type == "semantic":
                obj = mem[0]
            else:
                human, obj = split_by_possessive(mem[0])

            obj_loc = mem[2]
        object_embedding = self.embeddings(
            torch.tensor(self.word2idx[obj], device=self.device)
        )
        object_location_embedding = self.embeddings(
            torch.tensor(self.word2idx[obj_loc], device=self.device)
        )

        if memory_type == "semantic":
            final_embedding = torch.concat(
                [object_embedding, object_location_embedding]
            )

        elif memory_type in ["episodic", "short"]:
            human_embedding = self.embeddings(
                torch.tensor(self.word2idx[human], device=self.device)
            )

            if self.v1_params["include_human"] is None:
                final_embedding = torch.concat(
                    [object_embedding, object_location_embedding]
                )
            elif self.v1_params["include_human"] == "sum":
                final_embedding = [object_embedding + human_embedding]

                if self.v1_params["human_embedding_on_object_location"]:
                    final_embedding.append(object_location_embedding + human_embedding)
                else:
                    final_embedding.append(object_location_embedding)

                final_embedding = torch.concat(final_embedding)

            elif self.v1_params["include_human"] == "concat":
                final_embedding = torch.concat(
                    [human_embedding, object_embedding, object_location_embedding]
                )
        else:
            raise ValueError

        return final_embedding

    def make_embedding_v2(self, mem: list, memory_type: str) -> torch.Tensor:
        """Create one embedding vector with summation and concatenation.

        Embeddings for v1

        Args
        ----
        mem: memory as a quadruple: [head, relation, tail, num]

        Returns
        -------
        one embedding vector made from one memory element.

        """
        head_embedding = self.embeddings(
            torch.tensor(self.word2idx[mem[0]], device=self.device)
        )
        relation_embedding = self.embeddings(
            torch.tensor(self.word2idx[mem[1]], device=self.device)
        )
        tail_embedding = self.embeddings(
            torch.tensor(self.word2idx[mem[2]], device=self.device)
        )
        final_embedding = torch.concat(
            [head_embedding, relation_embedding, tail_embedding]
        )

        return final_embedding

    def create_batch(self, x: list, memory_type: str) -> torch.Tensor:
        """Create one batch from data.

        Args
        ----
        x: a batch of episodic, semantic, or short memories.
        memory_type: "episodic", "semantic", or "short"

        Returns
        -------
        batch of embeddings.

        """
        mem_pad = ["<PAD>", "<PAD>", "<PAD>", "<PAD>"]

        for mems in x:
            for _ in range(self.capacity[memory_type] - len(mems)):
                # this is a dummy entry for padding.
                mems.append(mem_pad)

        batch_embeddings = []
        for mems in x:
            embeddings = []
            for mem in mems:
                mem_emb = self.make_embedding(mem, memory_type)
                embeddings.append(mem_emb)
            embeddings = torch.stack(embeddings)
            batch_embeddings.append(embeddings)

        batch_embeddings = torch.stack(batch_embeddings)

        return batch_embeddings

    def forward(self, x: np.ndarray) -> torch.Tensor:
        """Forward-pass.

        Args
        ----
        x is a batch of memories. Each element of the batch is a np.ndarray of dict
        memories.

        """
        assert isinstance(x, np.ndarray)

        to_concat = []
        if "episodic" in self.memory_of_interest:
            batch_e = [sample["episodic"] for sample in x]
            batch_e = self.create_batch(batch_e, memory_type="episodic")
            lstm_out_e, _ = self.lstm_e(batch_e)
            fc_out_e = self.relu(
                self.fc_e1(self.relu(self.fc_e0(lstm_out_e[:, -1, :])))
            )
            to_concat.append(fc_out_e)

        if "semantic" in self.memory_of_interest:
            batch_s = [sample["semantic"] for sample in x]
            batch_s = self.create_batch(batch_s, memory_type="semantic")
            lstm_out_s, _ = self.lstm_s(batch_s)
            fc_out_s = self.relu(
                self.fc_s1(self.relu(self.fc_s0(lstm_out_s[:, -1, :])))
            )
            to_concat.append(fc_out_s)

        if "short" in self.memory_of_interest:
            batch_o = [sample["short"] for sample in x]
            batch_o = self.create_batch(batch_o, memory_type="short")
            lstm_out_o, _ = self.lstm_o(batch_o)
            fc_out_o = self.relu(
                self.fc_o1(self.relu(self.fc_o0(lstm_out_o[:, -1, :])))
            )
            to_concat.append(fc_out_o)

        fc_out_all = torch.concat(to_concat, dim=-1)

        # fc_out has the dimension of (batch_size, n_actions)
        fc_out = self.fc_final1(self.relu(self.fc_final0(fc_out_all)))

        return fc_out
