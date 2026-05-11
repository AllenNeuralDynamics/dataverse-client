"""
OData filter operator functions
Each function returns a filter string for the given operator.

Can be combined like this:
https://orgc1997c24.crm.dynamics.com/api/data/v9.2/crb81_dim_mice_bases?$count=true&$top=5&$select=crb81_mouse_id,crb81_date_of_birth&$filter=crb81_mouse_id%20eq%20%27810757%27

See https://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part1-protocol/odata-v4.0-errata03-os-part1-protocol-complete.html#_The_$filter_System

Operator Table:

| Operator | Description                | Example                              |
|----------|----------------------------|--------------------------------------|
| **Comparison Operators** |                            |                                      |
| eq       | Equal                      | Address/City eq 'Redmond'            |
| ne       | Not equal                  | Address/City ne 'London'             |
| gt       | Greater than               | Price gt 20                          |
| ge       | Greater than or equal      | Price ge 10                          |
| lt       | Less than                  | Price lt 20                          |
| le       | Less than or equal         | Price le 100                         |
| has      | Has flags                  | Style has Sales.Color'Yellow'        |
| **Logical Operators**    |                            |                                      |
| and      | Logical and                | Price le 200 and Price gt 3.5        |
| or       | Logical or                 | Price le 3.5 or Price gt 200         |
| not      | Logical negation           | not endswith(Description,'milk')     |
| **Arithmetic Operators** |                            |                                      |
| add      | Addition                   | Price add 5 gt 10                    |
| sub      | Subtraction                | Price sub 5 gt 10                    |
| mul      | Multiplication             | Price mul 2 gt 2000                  |
| div      | Division                   | Price div 2 gt 4                     |
| mod      | Modulo                     | Price mod 2 eq 0                     |
| **Grouping Operators**   |                            |                                      |
| ( )      | Precedence grouping        | (Price sub 5) gt 10                  |

Additional Functions Table:

| Function         | Example                                              |
|------------------|-----------------------------------------------------|
| **String Functions** |                                                     |
| contains         | contains(CompanyName,'freds')                        |
| endswith         | endswith(CompanyName,'Futterkiste')                  |
| startswith       | startswith(CompanyName,'Alfr')                       |
| length           | length(CompanyName) eq 19                            |
| indexof          | indexof(CompanyName,'lfreds') eq 1                   |
| substring        | substring(CompanyName,1) eq 'lfreds Futterkiste'     |
| tolower          | tolower(CompanyName) eq 'alfreds futterkiste'        |
| toupper          | toupper(CompanyName) eq 'ALFREDS FUTTERKISTE'        |
| trim             | trim(CompanyName) eq 'Alfreds Futterkiste'           |
| concat           | concat(concat(City,', '), Country) eq 'Berlin, Germany' |
| **Date Functions**   |                                                     |
| year             | year(BirthDate) eq 0                                 |
| month            | month(BirthDate) eq 12                               |
| day              | day(StartTime) eq 8                                  |
| hour             | hour(StartTime) eq 1                                 |
| minute           | minute(StartTime) eq 0                               |
| second           | second(StartTime) eq 0                               |
| fractionalseconds| fractionalseconds(StartTime) eq 0                    |
| date             | date(StartTime) ne date(EndTime)                     |
| time             | time(StartTime) le StartOfDay                        |
| totaloffsetminutes| totaloffsetminutes(StartTime) eq 60                 |
| now              | StartTime ge now()                                   |
| mindatetime      | StartTime eq mindatetime()                           |
| maxdatetime      | EndTime eq maxdatetime()                             |
| **Math Functions**   |                                                     |
| round            | round(Freight) eq 32                                 |
| floor            | floor(Freight) eq 32                                 |
| ceiling          | ceiling(Freight) eq 33                               |
| **Type Functions**   |                                                     |
| cast             | cast(ShipCountry,Edm.String)                         |
| isof             | isof(NorthwindModel.Order)                           |
| isof             | isof(ShipCountry,Edm.String)                         |
| **Geo Functions**    |                                                     |
| geo.distance     | geo.distance(CurrentPosition,TargetPosition)          |
| geo.length       | geo.length(DirectRoute)                              |
| geo.intersects   | geo.intersects(Position,TargetArea)                  |

"""

from datetime import datetime
from typing import Any, Literal, Optional


class Column(str):
    """Type class to indicate a string is a column name for formatting purposes."""


def format_value(value: Any) -> str:
    """Format a value for use in an OData filter expression.

    Examples:
    >>> format_value("London")
    "'London'"
    >>> format_value("'London'")
    "'London'"
    >>> format_value(Column("MyColumn"))
    'MyColumn'
    >>> format_value(datetime(2020, 1, 1))
    '2020-01-01T00:00:00'
    >>> format_value(True)
    'true'
    >>> format_value(None)
    'null'
    >>> format_value(42)
    '42'
    """
    if isinstance(value, Column):
        return value  # a string without quotes is assumed to be a column name
    elif isinstance(value, str):
        if value.startswith("'") and value.endswith("'"):
            return value  # already formatted as a string literal
        return f"'{value}'"  # strings should have single quotes
    elif isinstance(value, datetime):
        return f"{value.isoformat()}"
    elif isinstance(value, bool):
        return str(value).lower()
    elif value is None:
        return "null"
    else:
        return str(value)


def format_queries(
    filter: Optional[str] = None,
    order_by: Optional[str | list[str]] = None,
    top: Optional[int] = None,
    count: Optional[bool] = None,
    select: Optional[str | list[str]] = None,
    expand: Optional[str | list[str]] = None,
) -> str:
    """
    Format query parameters for a Dataverse API request.

    Args:
        filter: OData filter query. Defaults to None
        order_by: OData order by clause. Defaults to None
        top: OData top value. Defaults to None
        count: Include "@odata.count" in the response, counting matches. Defaults to None
        select: OData select clause. Defaults to None
        expand: OData expand clause. Defaults to None

    Returns:
        str: Formatted query string

    Examples:
        >>> format_queries(filter="Price gt 20", order_by="Name", top=5, select=["Name", "Price"])
        '?$filter=Price gt 20&$orderby=Name&$top=5&$select=Name,Price'

        >>> format_queries(filter=equal("Price", 20), order_by="Name", top=5, select=["Name", "Price"])
        '?$filter=Price eq 20&$orderby=Name&$top=5&$select=Name,Price'
    """
    queries = []
    if filter:
        queries.append(f"$filter={filter}")
    if order_by:
        if isinstance(order_by, str):
            order_by = [order_by]
        queries.append(f"$orderby={','.join(order_by)}")
    if top is not None:
        queries.append(f"$top={top}")
    if count is not None:
        queries.append(f"$count={str(count).lower()}")
    if select:
        if isinstance(select, str):
            select = [select]
        queries.append(f"$select={','.join(select)}")
    if expand:
        if isinstance(expand, str):
            expand = [expand]
        queries.append(f"$expand={','.join(expand)}")
    return "?" + "&".join(queries) if len(queries) else ""


def order_by(column: str, direction: Literal["asc", "desc"] = "asc") -> str:
    """OrderBy can be either ascending or descending,
    This is denoted by " asc" or " desc" after the column name.

    >>> order_by("Name")
    'Name asc'
    >>> order_by("Name", "desc")
    'Name desc'
    """
    return f"{column} {direction}"


# Comparison Operators


def equal(column: str, value: str) -> str:
    """Check equality. If value is a string, it should be wrapped in single quotes.
    Strings without quotes will be assumed to be column names.

    >>> equal('Price', 20)
    'Price eq 20'
    >>> equal('Address/City', "London")
    "Address/City eq 'London'"
    >>> equal('Address/City', Column("DesiredCity"))
    'Address/City eq DesiredCity'
    """
    return f"{column} eq {format_value(value)}"


def not_equal(column: str, value: str) -> str:
    """Not equal.

    >>> not_equal('Address/City', "'London'")
    "Address/City ne 'London'"
    """
    return f"{column} ne {format_value(value)}"


def greater_than(column: str, value: str) -> str:
    """Greater than.

    >>> greater_than('Price', 20)
    'Price gt 20'
    """
    return f"{column} gt {format_value(value)}"


def greater_than_or_equal(column: str, value: str) -> str:
    """Greater than or equal.

    >>> greater_than_or_equal('Price', 10)
    'Price ge 10'
    """
    return f"{column} ge {format_value(value)}"


def less_than(column: str, value: str) -> str:
    """Less than.

    >>> less_than('Price', 20)
    'Price lt 20'
    """
    return f"{column} lt {format_value(value)}"


def less_than_or_equal(column: str, value: str) -> str:
    """Less than or equal.

    >>> less_than_or_equal('Price', 100)
    'Price le 100'
    """
    return f"{column} le {format_value(value)}"


def has_flag(column: str, flag: str) -> str:
    """Has flags.

    >>> has_flag('Style', Column("Sales.Color'Yellow'"))
    "Style has Sales.Color'Yellow'"
    """
    return f"{column} has {format_value(flag)}"


def logical_and(left: str, right: str) -> str:
    """Logical and.

    >>> logical_and('Price le 200', 'Price gt 3.5')
    'Price le 200 and Price gt 3.5'
    """
    return f"{left} and {right}"


def logical_or(left: str, right: str) -> str:
    """Logical or.

    >>> logical_or('Price le 3.5', 'Price gt 200')
    'Price le 3.5 or Price gt 200'
    """
    return f"{left} or {right}"


def logical_not(expr: str) -> str:
    """Logical negation.

    >>> logical_not("endswith(Description,'milk')")
    "not endswith(Description,'milk')"
    """
    return f"not {expr}"


def add(left: str, right: str) -> str:
    """Addition.

    >>> add('Price', 5)
    'Price add 5'
    """
    return f"{left} add {right}"


def sub(left: str, right: str) -> str:
    """Subtraction.

    >>> sub('Price', 5)
    'Price sub 5'
    """
    return f"{left} sub {right}"


def mul(left: str, right: str) -> str:
    """Multiplication.

    >>> mul('Price', 2)
    'Price mul 2'
    """
    return f"{left} mul {right}"


def div(left: str, right: str) -> str:
    """Division.

    >>> div('Price', 2)
    'Price div 2'
    """
    return f"{left} div {right}"


def mod(left: str, right: str) -> str:
    """Modulo.

    >>> mod('Price', 2)
    'Price mod 2'
    """
    return f"{left} mod {right}"


def group(expr: str) -> str:
    """Precedence grouping.

    >>> group('Price sub 5')
    '(Price sub 5)'
    """
    return f"({expr})"


# Functions


# String Functions
def contains(column: str, value: str) -> str:
    """Check if column contains value.

    >>> contains('CompanyName', 'freds')
    "contains(CompanyName, 'freds')"
    """
    return f"contains({column}, '{value}')"


def endswith(column: str, value: str) -> str:
    """Check if column ends with value.

    >>> endswith('CompanyName', 'Futterkiste')
    "endswith(CompanyName, 'Futterkiste')"
    """
    return f"endswith({column}, '{value}')"


def startswith(column: str, value: str) -> str:
    """Check if column starts with value.

    >>> startswith('CompanyName', 'Alfr')
    "startswith(CompanyName, 'Alfr')"
    """
    return f"startswith({column}, '{value}')"


def length(column: str) -> str:
    """Return the length of a string column.

    >>> length('CompanyName')
    'length(CompanyName)'
    """
    return f"length({column})"


def indexof(column: str, value: str) -> str:
    """Return the index of value within a string column.

    >>> indexof('CompanyName', 'lfreds')
    "indexof(CompanyName, 'lfreds')"
    """
    return f"indexof({column}, '{value}')"


def substring(column: str, start: str, length: Optional[str] = None) -> str:
    """Return a substring of a string column.

    >>> substring('CompanyName', 1)
    'substring(CompanyName, 1)'
    >>> substring('CompanyName', 1, 5)
    'substring(CompanyName, 1, 5)'
    """
    if length is None:
        return f"substring({column}, {start})"
    else:
        return f"substring({column}, {start}, {length})"


def tolower(column: str) -> str:
    """Convert a string column to lowercase.

    >>> tolower('CompanyName')
    'tolower(CompanyName)'
    """
    return f"tolower({column})"


def toupper(column: str) -> str:
    """Convert a string column to uppercase.

    >>> toupper('CompanyName')
    'toupper(CompanyName)'
    """
    return f"toupper({column})"


def trim(column: str) -> str:
    """Trim whitespace from a string column.

    >>> trim('CompanyName')
    'trim(CompanyName)'
    """
    return f"trim({column})"


def concat(column1: str, column2: str) -> str:
    """Concatenate two string columns.

    >>> concat('City', 'Country')
    'concat(City, Country)'
    """
    return f"concat({column1}, {column2})"


class Filter:
    def __init__(self, expression: str):
        self.expression = expression

    def __call__(self, *args) -> str:
        return self.expression.format(*args)


# Date Functions
year = Filter("year({})")
month = Filter("month({})")
day = Filter("day({})")
hour = Filter("hour({})")
minute = Filter("minute({})")
second = Filter("second({})")
fractionalseconds = Filter("fractionalseconds({})")
date = Filter("date({})")
time = Filter("time({})")
totaloffsetminutes = Filter("totaloffsetminutes({})")
now = Filter("now()")
mindatetime = Filter("mindatetime()")
maxdatetime = Filter("maxdatetime()")

# Math Functions
round_ = Filter("round({})")
floor = Filter("floor({})")
ceiling = Filter("ceiling({})")

# Type Functions
cast = Filter("cast({}, {})")
isof = Filter("isof({})")
isof2 = Filter("isof({}, {})")

# Geo Functions
geo_distance = Filter("geo.distance({}, {})")
geo_length = Filter("geo.length({})")
geo_intersects = Filter("geo.intersects({}, {})")


########## Other query options

# ?$count=true&$top=5


def order_by(*columns: str) -> str:
    """Order results by one or more columns.

    >>> order_by('Name', 'Age')
    'orderby=Name,Age'
    """
    return "orderby=" + ",".join(columns)


def top(x: int) -> str:
    """Limit results to the top x records.

    >>> top(5)
    'top=5'
    """
    return f"top={x}"


def count(x: bool) -> str:
    """Include a count of matching records.

    >>> count(True)
    'count=True'
    """
    return f"count={x}"


def select(*columns: str) -> str:
    """Select specific columns to return.

    >>> select('Name', 'Age')
    'select=Name,Age'
    """
    return "select=" + ",".join(columns)


### Other odata queries not supported by dataverse:

# search
# skip
