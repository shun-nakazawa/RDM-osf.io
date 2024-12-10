import os
import json

def _id_to_name(id):
    return ' '.join(id.split('_'))

def _name_to_id(name):
    return '_'.join(name.split(' '))

def ensure_schema_structure(schema):
    schema['pages'] = schema.get('pages', [])
    schema['title'] = schema['name']
    schema['version'] = schema.get('version', 1)
    return schema

def resolve_question_path(path, current_tree_node, schema):
    node = current_tree_node
    while path.startswith('../'):
        path = path[3:]
        if node['parent'] is None:
            raise ValueError('question path is invalid: {} , {}'.format(path, schema['name']))
        node = {
            'siblings': node['parent']['siblings'],
            'parent': node['parent']['parent'],
            'question': None,
        }
    parts = path.split('/')
    if len(parts) == 0:
        raise ValueError('question path is invalid: {} , {}'.format(path, schema['name']))
    for part in parts:
        node = next(
            (
                {
                    'siblings': node['siblings'],
                    'parent': node,
                    'question': q,
                }
                for q in node['siblings']
                if (q.get('qid', None) or q.get('id', None)) == part
            ),
            None,
        )
        if node is None:
            raise ValueError('question path is invalid: {} , {}'.format(path, schema['name']))
    return node['question']

def parse_text_for_localization(text):
    parts = text.split('|')
    if len(parts) == 1:
        return parts[0], parts[0]
    else:
        return parts[0], parts[1]

def normalize_schema(schema):
    def normalize_question(current_tree_node):
        question = current_tree_node['question']
        required_if = question.get('required_if', None)
        message_required_if = question.get('message_required_if', None)
        if isinstance(required_if, dict):
            if message_required_if is None:
                raise ValueError('message_required_if is required if required_if is a dict: {}'.format(schema['name']))
        elif message_required_if is None and isinstance(required_if, str):
            target_tree_node = resolve_question_path(required_if, current_tree_node, schema)
            required_if_title_ja, required_if_title_en = parse_text_for_localization(target_tree_node.get('title'))
            question['message_required_if'] = '|'.join([
                'このフィールドか「{}」フィールドのいずれかを入力する必要があります。'.format(required_if_title_ja),
                'msgid "One of this field or \"{}\" field must be filled.'.format(required_if_title_en),
            ])
            question['required_if'] = {
                required_if: {
                    '$exists': False
                }
            }

        for subquestion in question.get('properties', []):
            normalize_question({
                'siblings': question['properties'],
                'parent': current_tree_node,
                'question': subquestion,
            })

    for page in schema['pages']:
        for question in page['questions']:
            normalize_question({
                'siblings': page['questions'],
                'parent': None,
                'question': question,
            })

    return schema

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)

OSF_META_SCHEMAS = [
    ensure_schema_structure(normalize_schema(from_json('osf-open-ended-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('osf-open-ended-3.json'))),
    ensure_schema_structure(normalize_schema(from_json('osf-standard-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('brandt-prereg-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('brandt-postcomp-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('prereg-prize.json'))),
    ensure_schema_structure(normalize_schema(from_json('erpc-prize.json'))),
    ensure_schema_structure(normalize_schema(from_json('confirmatory-general-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('egap-project-2.json'))),
    ensure_schema_structure(normalize_schema(from_json('veer-1.json'))),
    ensure_schema_structure(normalize_schema(from_json('aspredicted.json'))),
    ensure_schema_structure(normalize_schema(from_json('registered-report.json'))),
    ensure_schema_structure(normalize_schema(from_json('registered-report-3.json'))),
    ensure_schema_structure(normalize_schema(from_json('registered-report-4.json'))),
    ensure_schema_structure(normalize_schema(from_json('ridie-initiation.json'))),
    ensure_schema_structure(normalize_schema(from_json('ridie-complete.json'))),
    ensure_schema_structure(normalize_schema(from_json('osf-preregistration.json'))),
    ensure_schema_structure(normalize_schema(from_json('osf-preregistration-3.json'))),
    ensure_schema_structure(normalize_schema(from_json('egap-registration.json'))),
    ensure_schema_structure(normalize_schema(from_json('egap-registration-3.json'))),
    ensure_schema_structure(normalize_schema(from_json('e-rad-metadata-1.json'))),
    ensure_schema_structure(normalize_schema(from_json('ms2-mibyodb-metadata.json'))),
]

METASCHEMA_ORDERING = (
    'Prereg Challenge',
    'OSF Preregistration',
    'Open-Ended Registration',
    'Preregistration Template from AsPredicted.org',
    'Registered Report Protocol Preregistration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion',
    "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration",
    'Election Research Preacceptance Competition',
    'RIDIE Registration - Study Initiation',
    'RIDIE Registration - Study Complete',
    'EGAP Registration',
    '公的資金による研究データのメタデータ登録',
    'ムーンショット目標2データベース（未病DB）のメタデータ登録',
)
