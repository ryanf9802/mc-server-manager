namespace McServerManager.Domain.Models;

public sealed record WorldFileSet(
    string ServerPropertiesText,
    string WhitelistJsonText);

