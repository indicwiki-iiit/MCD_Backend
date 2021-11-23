import itertools

QUESTION_MAP = {
    'text': 'Descriptive',
    'mcq-single-correct': 'MCQ',
    'mcq-multiple-correct': 'MCQ multiple correct',
    'translation': 'Translation',
}


def get_all_combs(elements):
    combs = []
    for i in range(1, len(elements) + 1):
        combs.extend(itertools.combinations(elements, i))
    return combs


def get_dict_combs(options):
    keys = options.keys()
    values = (options[key] for key in keys)
    combinations = [dict(zip(keys, combination)) for combination in itertools.product(*values)]
    combinations = [{k: v for k, v in c.items() if v is not None} for c in combinations]
    return combinations
