import re


class BulletPointAuditor:
    """Domain tier: flags experience bullet points that lack quantified impact.

    A pure business rule with no knowledge of FastAPI, files, or storage. It
    takes a list of bullet-point strings and returns a new list containing only
    the bullets that FAILED the audit (i.e. have no number in them).

    Rationale: strong resume bullets quantify impact ("reduced load time by
    40%", "managed 12 engineers"). A bullet with no digit is a candidate for
    improvement, which is exactly what the AI refinement feature (Issue #4)
    will later rewrite.
    """

    # Matches any digit 0-9 anywhere in the string. This deterministically
    # catches "40%", "$1.2M", "12 engineers", "increased by 3x", etc. Compiled
    # once at class-definition time for efficiency.
    _NUMBER_PATTERN = re.compile(r"\d")

    def flag_unquantified(self, bullets: list[str]) -> list[str]:
        """Return only the bullet points that contain no number.

        Args:
            bullets: a list where each string is a single experience bullet.

        Returns:
            A new list of the bullets that failed the audit (no digit found).
            Bullets that already contain a number are considered quantified and
            are excluded from the result.
        """
        flagged = []
        for bullet in bullets:
            # search() returns None when the bullet has no digit at all.
            if self._NUMBER_PATTERN.search(bullet) is None:
                flagged.append(bullet)
        return flagged
