using McServerManager.Application.Worlds;

namespace McServerManager.UnitTests;

public sealed class WorldNameGeneratorTests
{
    [Fact]
    public void CreateSlug_NormalizesMixedInput()
    {
        var slug = WorldNameGenerator.CreateSlug(" Weekend Vanilla++ 2026 ");

        Assert.Equal("weekend-vanilla-2026", slug);
    }

    [Fact]
    public void CreateSlug_FallsBackWhenNameContainsNoLettersOrDigits()
    {
        var slug = WorldNameGenerator.CreateSlug("!!!");

        Assert.Equal("world", slug);
    }
}

