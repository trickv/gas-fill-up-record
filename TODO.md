# TODO

## Future Enhancements

### Handle vacation fill-ups in different categories
On 29th September 2024, we had two fill-ups while on vacation that got classified in a different YNAB category (not "Gas for car").

**Challenge**: How to find and include these transactions?

**Possible approaches:**
1. Add support for multiple category IDs
2. Use payee name matching instead of/in addition to category filtering
3. Add manual import feature for one-off transactions
4. Look for transactions in "Travel" or "Vacation" categories that match gas station payees

This is interesting because it highlights the edge case where legitimate gas purchases might be categorized differently based on context (vacation spending vs. regular car maintenance).
