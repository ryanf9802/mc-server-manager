using McServerManager.Application.Validation;

namespace McServerManager.UnitTests;

public sealed class WhitelistValidatorTests
{
    private readonly WhitelistValidator _validator = new();

    [Fact]
    public void Validate_AcceptsExpectedShape()
    {
        var result = _validator.Validate(
            """
            [
              {
                "name": "ryanf",
                "uuid": "00000000-0000-0000-0000-000000000000"
              }
            ]
            """);

        Assert.True(result.IsValid);
    }

    [Fact]
    public void Validate_RejectsMissingRequiredFields()
    {
        var result = _validator.Validate("[{\"name\":\"ryanf\"}]");

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, issue => issue.Code == "whitelist_uuid_missing");
    }
}

