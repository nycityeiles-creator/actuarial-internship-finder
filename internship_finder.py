# Actuarial Internship Finder
# This program will eventually search the web for actuarial internships.

from datetime import datetime


SEARCH_TERMS = [
    "actuarial intern",
    "actuarial internship",
    "actuary intern",
    "actuarial analyst intern",
    "P&C actuarial intern",
    "life actuarial intern",
    "health actuarial intern",
    "retirement actuarial intern",
]


def main():
    print("Actuarial Internship Finder")
    print("----------------------------")
    print("Search started:", datetime.now())

    print("\nWe will search for:")

    for term in SEARCH_TERMS:
        print("-", term)


if __name__ == "__main__":
    main()
