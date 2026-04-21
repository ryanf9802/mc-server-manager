using McServerManager.Application.Validation;

namespace McServerManager.UnitTests;

public sealed class ServerPropertiesValidatorTests
{
    private readonly ServerPropertiesValidator _validator = new();

    [Fact]
    public void Validate_AllowsCommentsBlanksAndAssignments()
    {
        var result = _validator.Validate(
            """
            # Minecraft server configuration
            motd=Weekend World

            max-players=8
            """);

        Assert.True(result.IsValid);
    }

    [Fact]
    public void Validate_RejectsNonAssignmentLines()
    {
        var result = _validator.Validate("motd=Weekend\nthis is broken");

        Assert.False(result.IsValid);
        Assert.Contains(result.Issues, issue => issue.LineNumber == 2);
    }
}

