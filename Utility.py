def get_triples_from(subject, predicate, object, in_set, out_set, pred_set):
    if subject is not None and predicate is not None and object is not None:
        if (predicate, object) in out_set.get(subject, ()):
            return {(subject, predicate, object)} if (predicate, object) in out_set.get(subject, ()) else set()
        return ()

    if subject is not None:
        pairs = out_set.get(subject, ())
        return {
            (subject, p, o)
            for p, o in pairs
            if (predicate is None or p == predicate) and (object is None or o == object)
        }

    if object is not None:
        pairs = in_set.get(object, ())
        return {
            (s, p, object)
            for p, s in pairs
            if (predicate is None or p == predicate) and (subject is None or s == subject)
        }

    if predicate is not None:
        pairs = pred_set.get(predicate, ())
        return {
            (s, predicate, o)
            for s, o in pairs
            if (subject is None or s == subject) and (object is None or o == object)
        }

    all_triples = set()
    for p, pairs in pred_set.items():
        for s, o in pairs:
            all_triples.add((s, p, o))
    return all_triples