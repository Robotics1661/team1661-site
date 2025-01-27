__all__ = []

import typing

T = typing.TypeVar('T')


def permutations(elements: set[T]) -> typing.Generator[typing.List[T], None, None]:
    """
    Generate all permutations of the given elements.

    :param elements: The elements to permute.
    :return: A generator of permutations.
    """

    if len(elements) == 0:
        yield []
    else:
        for element in elements:
            remaining_elements = elements - {element}
            for permutation in permutations(remaining_elements):
                yield [element] + permutation


def find_best_permutation(elements: set[T], score_fn: typing.Callable[[typing.List[T]], float], good_enough: float = float("inf")) -> typing.List[T]:
    """
    Find the permutation of elements that maximizes the score function.

    :param elements: The elements to permute.
    :param score_fn: The scoring function. Higher scores are better. Negative scores are allowed.
    :param good_enough: If a score of this value or higher is found, return immediately.
    :return: The best permutation.
    """

    best_permutation = None
    best_score = float('-inf')
    for permutation in permutations(elements):
        score = score_fn(permutation)
        if score > best_score:
            best_permutation = permutation
            best_score = score
            if score >= good_enough:
                break

    return best_permutation or list(elements)
