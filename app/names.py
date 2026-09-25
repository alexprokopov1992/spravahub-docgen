def _fallback(last_name: str, first_name: str, patronymic: str):
    nom = " ".join(x for x in (last_name, first_name, patronymic) if x)
    return {
        "nom": nom, "gen": nom, "dat": nom, "acc": nom,
        "ins": nom, "loc": nom, "voc": nom,
    }

def decline_name(last_name: str, first_name: str, patronymic: str, gender: str):
    last_name = last_name.strip()
    first_name = first_name.strip()
    patronymic = patronymic.strip()
    try:
        import shevchenko

        gender_value = {
            "male": "masculine",
            "female": "feminine",
            "masculine": "masculine",
            "feminine": "feminine",
        }.get(gender, gender)

        data = {
            "family_name": last_name,
            "given_name": first_name,
            "patronymic_name": patronymic,
            "gender": gender_value,
        }

        funcs = {
            "nom": getattr(shevchenko, "in_nominative"),
            "gen": getattr(shevchenko, "in_genitive"),
            "dat": getattr(shevchenko, "in_dative"),
            "acc": getattr(shevchenko, "in_accusative"),
            "ins": getattr(shevchenko, "in_ablative"),
            "loc": getattr(shevchenko, "in_locative"),
            "voc": getattr(shevchenko, "in_vocative"),
        }

        def join(result):
            return " ".join(
                x for x in (
                    result.get("family_name"),
                    result.get("given_name"),
                    result.get("patronymic_name"),
                ) if x
            )

        result = {key: join(fn(**data)) for key, fn in funcs.items()}
    except Exception:
        result = _fallback(last_name, first_name, patronymic)

    result["nom_header"] = " ".join(
        x for x in (last_name.upper(), first_name, patronymic) if x
    )
    result["signature_name"] = " ".join(
        x for x in (first_name, last_name.upper()) if x
    )
    return result
