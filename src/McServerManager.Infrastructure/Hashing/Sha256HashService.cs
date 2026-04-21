using System.Security.Cryptography;
using System.Text;
using McServerManager.Application.Activation;

namespace McServerManager.Infrastructure.Hashing;

public sealed class Sha256HashService : IHashService
{
    public string ComputeSha256(string content)
    {
        var bytes = Encoding.UTF8.GetBytes(content);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash);
    }
}
