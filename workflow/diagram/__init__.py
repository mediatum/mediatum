# -*- coding: utf-8 -*-

# Copyright (C) since 2007, Technical University of Munich (TUM) and mediaTUM authors
# SPDX-License-Identifier: AGPL-3.0-or-later

# graphviz is our only implementation, just import it, ignoring the config value `config.workflowdiagram_type`

from __future__ import division
from __future__ import print_function

from .graphviz import send_workflow_diagram
